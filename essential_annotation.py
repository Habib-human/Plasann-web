import os
import subprocess as sp
from Bio.Seq import Seq
import pandas as pd
from Bio.Blast import NCBIXML
from Bio.SeqRecord import SeqRecord
from Bio.SeqFeature import SeqFeature, FeatureLocation
from Bio import SeqIO
from concurrent.futures import ProcessPoolExecutor
from io import StringIO
import re
from datetime import datetime
from Bio import Entrez, SeqIO
from Bio.SeqIO.InsdcIO import UndefinedSequenceError



def find_fasta_file(plasmid, pathofdir):
    extensions = ['.fasta', '.fa', '.fsa', '.fna']
    for ext in extensions:
        fasta_path = os.path.join(pathofdir, f"{plasmid}{ext}")
        if os.path.exists(fasta_path):
            return fasta_path
    return None  # No file found


def getsequencelength(plasmid, pathofdir):
    fasta_file = find_fasta_file(plasmid, pathofdir)
    if not fasta_file:
        print(f"No FASTA file found for {plasmid}.")
        return "File not found"  # or handle it another way as needed

    length_of_fasta = sp.getoutput(f"awk '{{if(NR>1)print}}' {fasta_file} | awk '{{print length}}' | awk '{{n += $1}}; END{{print n}}'")
    return length_of_fasta

def getthesequences(plasmid, pathofdir):
    fasta_file = find_fasta_file(plasmid, pathofdir)
    if not fasta_file:
        print(f"No FASTA file found for {plasmid}.")
        return "File not found"  # or handle it another way as needed

    only_sequence = sp.getoutput(f"awk '{{if(NR>1)print}}' {fasta_file} | tr -d '\r\n'")
    return only_sequence

'''def getpositionsofCDS(plasmid):
    os.system(f"grep CDS tmp_files/{plasmid}prodigal.gbk | grep -o '[[:digit:]]*' > tmp_files/positions.txt")  #this one gets all the positions of CDS
    with open("tmp_files/positions.txt", "r") as file_obj:
        file_data = file_obj.read() 
        lines = file_data.splitlines() 
        list_of_positions = [(lines[i], lines[i+1]) for i in range(0, len(lines)-1,2)]
    #os.remove("../tmp_files/positions.txt")
    return list_of_positions'''

import re

def getpositionsofCDS(plasmid):
    """
    Extracts the positions of CDS from a GenBank file.

    Args:
        plasmid (str): The name of the plasmid file (without path).

    Returns:
        list of tuple: A list of (start, end) positions for CDS.
    """
    file_path = f"tmp_files/{plasmid}prodigal.gbk"

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            file_content = file.read()
    except UnicodeDecodeError:
        # Fallback to another encoding if utf-8 fails
        with open(file_path, "r", encoding="latin-1") as file:
            file_content = file.read()

    # Extract CDS positions using regex
    matches = re.findall(r'CDS\s+(?:complement\()?(\d+)\.\.(\d+)', file_content)
    list_of_positions = [(int(start), int(end)) for start, end in matches]

    return list_of_positions


import subprocess

def calculate_gc_content(fasta_file):
    total_bases = 0
    gc_count = 0

    with open(fasta_file, 'r') as f:
        for line in f:
            if not line.startswith(">"):  # Skip header lines
                sequence = line.strip().upper()
                total_bases += len(sequence)
                gc_count += sequence.count("G") + sequence.count("C")

    if total_bases == 0:
        raise ValueError("No sequence data found in the FASTA file.")

    gc_percentage = (gc_count / total_bases) * 100
    return gc_percentage






# This one gets the complement strat and end positions 
'''def complementpositions(plasmid):
    os.system(f"grep complement  tmp_files/{plasmid}prodigal.gbk |awk '{{print $2}}'|grep -o '([^)]*)'| awk -F\\. '{{print $1}}'| grep -o '[[:digit:]]*' > tmp_files/complementstarting.txt")  #This one gets all the complement positions [starting]
    with open("tmp_files/complementstarting.txt","r") as file:
        list_of_complementstart = []
        for line in file:
            line = line.strip()
            list_of_complementstart.append(line)
    #os.remove("../tmp_files/complementstarting.txt")

    os.system(f"grep complement  tmp_files/{plasmid}prodigal.gbk |awk '{{print $2}}'|grep -o '([^)]*)'| awk -F\\. '{{print $3}}'| grep -o '[[:digit:]]*' > tmp_files/complementending.txt")   #This one gets all the complement positions [ending]
    with open("tmp_files/complementending.txt","r") as file:
        list_of_complementend = []
        for line in file:
            line = line.strip()
            list_of_complementend.append(line)
    #os.remove("../tmp_files/complementending.txt")
    return list_of_complementstart, list_of_complementend'''

def complementpositions(plasmid):
    """Extract complement positions using pure Python parsing."""
    complement_starts = []
    complement_ends = []
    
    try:
        with open(f"tmp_files/{plasmid}prodigal.gbk", "r") as file:
            for line in file:
                # Look for CDS features with complement
                if 'CDS' in line and 'complement' in line:
                    try:
                        # Extract the position part between complement(...)
                        pos_part = line.split('complement(')[1].split(')')[0]
                        if '..' in pos_part:
                            start, end = pos_part.split('..')
                            # Clean and convert to integers
                            start = int(start)
                            end = int(end)
                            complement_starts.append(start)
                            complement_ends.append(end)
                    except (IndexError, ValueError):
                        continue
    
        # Write clean start positions to file
        with open("tmp_files/complementstarting.txt", "w") as f:
            for start in complement_starts:
                f.write(f"{start}\n")
        
        # Write clean end positions to file
        with open("tmp_files/complementending.txt", "w") as f:
            for end in complement_ends:
                f.write(f"{end}\n")
        
        return complement_starts, complement_ends
        
    except Exception as e:
        print(f"Error processing complement positions: {e}")
        return [], []


def getlistofDNACDS(list_of_positions,full_sequence):
    list_of_cds = []
    for i in range(len(list_of_positions)):
        x = int(list_of_positions[i][0])-1
        y = int(list_of_positions[i][1])-1
        list_of_cds.append(full_sequence[x:y])
    return list_of_cds


#The one that makes a query file from the list of coding sequences
def makequeryfastafordbsearch(list_of_cds):
    query_file = open(r'tmp_files/Query_Fasta.fsa', 'w+')
    out = '\n'.join(['>Coding Sequence' + str(i+1) + "\n" + j for i,j in enumerate(list_of_cds)])
    query_file.write(out)
    query_file.close()

def makedatabasefromcsvfile(database_name):
    database = pd.read_csv(database_name,low_memory=False)
    database['identifier'] = database['Gene Name'] + '#"' + database.index.astype(str) + '"'
    target_file = open(r'tmp_files/target_fasta.fsa','w+')
    out1 = '\n'.join(['>'+str(database['identifier'][i])+"\n"+str(database['Translation'][i]) for i in range(len(database))])
    target_file.write(out1)
    target_file.close()
    if not os.path.exists("makedb_folder/blastdb"):
        os.makedirs("makedb_folder/blastdb")
    os.system('makeblastdb -in tmp_files/target_fasta.fsa -dbtype prot -out makedb_folder/blastdb/custom_database > /dev/null 2>&1')
    return database



def extract_gene_info(gene_string):
    if pd.isna(gene_string):
        return None, None
    try:
        gene_name, index_part = gene_string.split('#"')
        index_part = index_part.rstrip('"')  # Remove the trailing quote
        index = int(index_part)  # Convert index to integer
        return gene_name, index
    except ValueError:
        return None, None


def select_gene_row(df):
    # First try to filter rows with 'Percent Identity' = 100
    filtered_df = df[df['Pident'] >= 85]
    
    # If no rows with 100% identity, or less than 10 rows with 100% identity, consider rows with 'Percent Identity' > 90%
    #if filtered_df.empty or len(filtered_df) < 5:
    if filtered_df.empty:
        filtered_df = df[df['Pident'] > 70]
    
    # Count the occurrences of each gene
    gene_counts = filtered_df['Gene Name'].value_counts()
    max_occurrence = gene_counts.max()
    # Identify genes with the maximum occurrence
    most_frequent_genes = gene_counts[gene_counts == max_occurrence].index.tolist()
    # Filter for the most frequent genes
    most_frequent_df = filtered_df[filtered_df['Gene Name'].isin(most_frequent_genes)]
    # Select the row with the lowest E-value for each gene
    selected_rows = most_frequent_df.loc[most_frequent_df.groupby('Gene Name')['E-value'].idxmin()]
    return selected_rows

def remove_similar_positions(df):
    df['Start Position Range'] = df['Start Position'] // 50
    df['End Position Range'] = df['End Position'] // 50
    
    # Group by Start Position Range and End Position Range and select row with minimum E-value in each group
    df = df.loc[df.groupby(['Start Position Range', 'End Position Range'])['E-value'].idxmin()]

    # Drop the temporary columns used for grouping
    df = df.drop(columns=['Start Position Range', 'End Position Range'])
    
    return df


def run_blast(sequence, index, list_of_positions):
    query_path = f'tmp_files/query_{index}.fsa'
    result_path = f'tmp_files/result_{index}.xml'
    
    # Write the sequence to a temporary FASTA file
    with open(query_path, 'w') as query_file:
        query_file.write(f'>Coding Sequence{index}\n{sequence}')
    
    # Run BLAST
    os.system(f'blastx -query {query_path} -db makedb_folder/blastdb/custom_database -outfmt 5 -out {result_path}')
    
    # Parse BLAST result
    with open(result_path, 'r') as result_file:
        records = NCBIXML.parse(result_file)
        item = next(records)
        
        results = []
        for alignment in item.alignments:
            for hsp in alignment.hsps:
                if hsp.expect < 0.001 and hsp.identities / alignment.length * 100 > 60:
                    results.append({
                        "Name of Query": f"Coding Sequence{index}",
                        "Start Position": list_of_positions[index][0],
                        "End Position": list_of_positions[index][1],
                        "Title": alignment.title.split(' ')[1],
                        "Length": alignment.length,
                        "Score": hsp.score,
                        "Pident": hsp.identities / alignment.length * 100,
                        "Gaps": hsp.gaps,
                        "E-value": hsp.expect,
                        "Sequence": hsp.query,
                        "Query Length": len(sequence),
                        "Subject Length": alignment.length
                    })
        return results

def initial_blast_against_database(list_of_cds, list_of_positions, database):
    with ProcessPoolExecutor() as executor:
        futures = [executor.submit(run_blast, seq, idx, list_of_positions) for idx, seq in enumerate(list_of_cds)]
        results = [future.result() for future in futures]

    # Flatten list of lists
    flat_results = [item for sublist in results for item in sublist]
    
    # Create DataFrame from results
    final_dataframe = pd.DataFrame(flat_results)
    selected_rows_per_query = pd.DataFrame()
    if not final_dataframe.empty:
        final_dataframe['Gene Name'], final_dataframe['index'] = zip(*final_dataframe['Title'].apply(extract_gene_info))
        final_dataframe.dropna(subset=['Gene Name', 'index'], inplace=True)
        
        # Further processing
        unique_query_names = final_dataframe['Name of Query'].unique()
        selected_rows_per_query = pd.concat([select_gene_row(final_dataframe[final_dataframe['Name of Query'] == query_name]) for query_name in unique_query_names])
        selected_rows_per_query.reset_index(drop=True, inplace=True)
        
        # Append product and category information
        selected_rows_per_query['Category'] = [database['Category'][int(index)] for index in selected_rows_per_query['index']]
        selected_rows_per_query['Product'] = [database['Product'][int(index)] for index in selected_rows_per_query['index']]
        
        # Clean up DataFrame
        selected_rows_per_query.drop(['index', 'Title', 'Pident', 'Query Length', 'Subject Length'], axis=1, inplace=True)

    return selected_rows_per_query




def blast_against_oric_dataframe(oric_database, plasmid, path):
    if not os.path.exists("makedb_folder/oricdb"):
        os.makedirs("makedb_folder/oricdb")
        # Make ORIC database from the fasta file
    os.system(f'makeblastdb -in {oric_database} -dbtype nucl -out makedb_folder/oricdb/oric_database > /dev/null 2>&1')

    # Find the correct FASTA file
    fasta_file_path = find_fasta_file(plasmid, path)
    if not fasta_file_path:
        print(f"No valid FASTA file found for {plasmid}.")
        return None

    # Run BLAST against the ORIC database
    os.system(f'blastn -query "{fasta_file_path}" -db makedb_folder/oricdb/oric_database -outfmt 5 -out tmp_files/resultoric.xml')

    # Initialize lists to store information
    name_of_query, titlelist, lengthlist, scorelist, gaplist, evallist, sequencelist, startpos, endpos, product_list, index = ([] for i in range(11))

    # Open and parse the BLAST XML result file
    with open("tmp_files/resultoric.xml", "r") as result:
        records = NCBIXML.parse(result)
        item = next(records)
        j = 1  # Start the counter from 1

        for alignment in item.alignments:
            for hsp in alignment.hsps:
                if hsp.expect < 0.01 and hsp.identities / alignment.length * 100 > 90:
                    name_of_query.append("OriC Sequence" + str(j))
                    startpos.append(hsp.query_start)
                    endpos.append(hsp.query_end)
                    titlelist.append("oriC")
                    lengthlist.append(alignment.length)
                    scorelist.append(hsp.score)
                    gaplist.append(hsp.gaps)
                    evallist.append(hsp.expect)
                    sequencelist.append(hsp.query)
                    product_list.append('origin of replication')
                    index.append(None)

    # Create the DataFrame from the collected data
    oric_dataframe = pd.DataFrame({
        "Query Name": name_of_query,
        "Gene Name": titlelist,
        "Length": lengthlist,
        "Score": scorelist,
        "Gaps": gaplist,
        "E-value": evallist,
        "Sequence": sequencelist,
        "Start Position": startpos,
        "End Position": endpos,
        "Product": product_list,
        "index": index
    })

    return oric_dataframe


def blast_against_orit_dataframe(orit_database, plasmid, path):
    if not os.path.exists("makedb_folder/oritdb"):
        os.makedirs("makedb_folder/oritdb")
    # Make ORIT database from the fasta file we have
    os.system(f'makeblastdb -in {orit_database} -dbtype nucl -out makedb_folder/oritdb/orit_database > /dev/null 2>&1')

    # Find the correct FASTA file
    fasta_file_path = find_fasta_file(plasmid, path)
    if not fasta_file_path:
        print(f"No valid FASTA file found for {plasmid}.")
        return None

    # Run BLAST against the ORIT database
    os.system(f'blastn -query "{fasta_file_path}" -db makedb_folder/oritdb/orit_database -outfmt 5 -out tmp_files/resultorit.xml')

    # Initialize lists to store information
    name_of_query, titlelist, lengthlist, scorelist, gaplist, evallist, sequencelist, startpos, endpos, product_list, index = ([] for i in range(11))

    # Open and parse the BLAST XML result file
    with open("tmp_files/resultorit.xml", "r") as result:
        records = NCBIXML.parse(result)
        item = next(records)
        j = 1  # Start the counter from 1

        for alignment in item.alignments:
            for hsp in alignment.hsps:
                if hsp.expect < 0.01 and hsp.identities / alignment.length * 100 > 90:
                    name_of_query.append("Orit Sequence" + str(j))
                    startpos.append(hsp.query_start)
                    endpos.append(hsp.query_end)
                    titlelist.append("oriT")
                    lengthlist.append(alignment.length)
                    scorelist.append(hsp.score)
                    gaplist.append(hsp.gaps)
                    evallist.append(hsp.expect)
                    sequencelist.append(hsp.query)
                    product_list.append('origin of transfer')
                    index.append(None)
                    j += 1  # Increment the counter after appending

    # Create the DataFrame from the collected data
    orit_dataframe = pd.DataFrame({
        "Query Name": name_of_query,
        "Gene Name": titlelist,
        "Length": lengthlist,
        "Score": scorelist,
        "Gaps": gaplist,
        "E-value": evallist,
        "Sequence": sequencelist,
        "Start Position": startpos,
        "End Position": endpos,
        "Product": product_list,
        "index": index,
    })

    return orit_dataframe

def blast_against_transposon_database(transposon_database, plasmid, path, selected_rows_per_query):
    if not os.path.exists("makedb_folder/transposondb"):
        os.makedirs("makedb_folder/transposondb")
    # Make transposon database from the fasta file we have
    os.system(f'makeblastdb -in {transposon_database} -dbtype nucl -out makedb_folder/transposondb/transposon_database > /dev/null 2>&1')

    # Find the correct FASTA file
    fasta_file_path = find_fasta_file(plasmid, path)
    if not fasta_file_path:
        print(f"No valid FASTA file found for {plasmid}.")
        return None

    # Run BLAST against the transposon database
    os.system(f'blastn -query "{fasta_file_path}" -db makedb_folder/transposondb/transposon_database -outfmt 5 -out tmp_files/resulttransposon.xml')

    # Initialize lists to store information
    name_of_query, titlelist, lengthlist, scorelist, gaplist, evallist, sequencelist, startpos, endpos, product_list = ([] for i in range(10))

    # Open and parse the BLAST XML result file
    with open("tmp_files/resulttransposon.xml", "r") as result:
        records = NCBIXML.parse(result)
        item = next(records)
        j = 1  # Start the counter from 1

        for alignment in item.alignments:
            for hsp in alignment.hsps:
                if hsp.expect < 0.01 and hsp.identities / alignment.length * 100 > 90:
                    name_of_query.append("transposon Sequence" + str(j))
                    startpos.append(hsp.query_start)
                    endpos.append(hsp.query_end)
                    titlelist.append(alignment.title.split(' ')[1])
                    lengthlist.append(alignment.length)
                    scorelist.append(hsp.score)
                    gaplist.append(hsp.gaps)
                    evallist.append(hsp.expect)
                    sequencelist.append(hsp.query)
                    product_list.append('Mobile Genetic Element')
                    j += 1  # Increment the counter after appending

    # Create the DataFrame from the collected data
    transposon_dataframe = pd.DataFrame({
        "Query Name": name_of_query,
        "Gene Name": titlelist,
        "Length": lengthlist,
        "Score": scorelist,
        "Gaps": gaplist,
        "E-value": evallist,
        "Sequence": sequencelist,
        "Start Position": startpos,
        "End Position": endpos,
        "Product": product_list,
    })

    return transposon_dataframe



def blast_against_replicon_database(replicon_database, plasmid, path):
    if not os.path.exists("makedb_folder/repdb"):
        os.makedirs("makedb_folder/repdb")
    # Make replicon database from the fasta file we have
    os.system(f'makeblastdb -in {replicon_database} -dbtype nucl -out makedb_folder/repdb/plasmidfinder_database > /dev/null 2>&1')

    # Find the correct FASTA file
    fasta_file_path = find_fasta_file(plasmid, path)
    if not fasta_file_path:
        print(f"No valid FASTA file found for {plasmid}.")
        return None

    # Run BLAST against the replicon database
    os.system(f'blastn -query "{fasta_file_path}" -db makedb_folder/repdb/plasmidfinder_database -outfmt 5 -out tmp_files/resultplasmidfinder.xml')

    # Initialize lists to store information
    name_of_query, titlelist, lengthlist, scorelist, gaplist, evallist, sequencelist, startpos, endpos, product_list = ([] for i in range(10))

    # Open and parse the BLAST XML result file
    with open("tmp_files/resultplasmidfinder.xml", "r") as result:
        records = NCBIXML.parse(result)
        item = next(records)
        j = 1  # Start the counter from 1

        for alignment in item.alignments:
            for hsp in alignment.hsps:
                if hsp.expect < 0.01 and hsp.identities / alignment.length * 100 > 90:
                    name_of_query.append("Replicon " + str(j))
                    startpos.append(hsp.query_start)
                    endpos.append(hsp.query_end)
                    titlelist.append(alignment.title.split(' ')[1])
                    lengthlist.append(alignment.length)
                    scorelist.append(hsp.score)
                    gaplist.append(hsp.gaps)
                    evallist.append(hsp.expect)
                    sequencelist.append(hsp.query)
                    product_list.append('Replicon type')
                    j += 1  # Increment the counter after appending

    # Create the DataFrame from the collected data
    replicon_dataframe = pd.DataFrame({
        "Query Name": name_of_query,
        "Gene Name": titlelist,
        "Length": lengthlist,
        "Score": scorelist,
        "Gaps": gaplist,
        "E-value": evallist,
        "Sequence": sequencelist,
        "Start Position": startpos,
        "End Position": endpos,
        "Product": product_list
    })

    replicon_dataframe = remove_similar_positions(replicon_dataframe)
    replicon_dataframe.reset_index(drop=True, inplace=True)
    replicon_dataframe = replicon_dataframe.rename(columns={"Query Name": "Name of Query"})
    replicon_dataframe['Category'] = 'Replicon'
    return replicon_dataframe




def make_genbank_file(only_sequence, final_df, genbank_path, plasmid):
    # Read complement start and end positions from the text files
    with open('tmp_files/complementstarting.txt', 'r') as file:
        complement_starts = [int(line.strip()) for line in file.readlines()]

    with open('tmp_files/complementending.txt', 'r') as file:
        complement_ends = [int(line.strip()) for line in file.readlines()]

    # Handle None sequence by providing an empty string
    sequence_data = '' if only_sequence is None else only_sequence

    record = SeqRecord(
        Seq(sequence_data),  # Initialize with a sequence or an empty string
        id="00000",
        name=plasmid,
        description="Genbank file for Plasmid " + plasmid,
        annotations={"molecule_type": "DNA"}  # Specify the molecule type
    )

    final_df['Start Position'] = pd.to_numeric(final_df['Start Position'], errors='coerce').fillna(0).astype(int)
    final_df['End Position'] = pd.to_numeric(final_df['End Position'], errors='coerce').fillna(0).astype(int)

    # Function to determine if a position is complement
    def is_complement(start, end, comp_starts, comp_ends):
        return start in comp_starts and end in comp_ends

    def determine_feature_type(category):
        if category == "Mobile Genetic Element":
            return "MGE"
        elif category == "Origin of Transfer":
            return "OriT"
        elif category == "Origin of Replication":
            return "OriC"
        elif category == "Replicon":
            return "Replicon"
        else:
            return "CDS"  # Default feature type

    # Add features to the GenBank record
    for idx, row in final_df.iterrows():
        feature_type = determine_feature_type(row['Category'])

        start_position = row['Start Position'] - 1
        end_position = row['End Position']

        # Check if the end position is greater than or equal to the start position
        if end_position < start_position:
            print(f"Skipping invalid feature with start {start_position + 1} and end {end_position}")
            continue

        # Determine if the feature is on the complement strand
        if is_complement(row['Start Position'], row['End Position'], complement_starts, complement_ends):
            location = FeatureLocation(start_position, end_position, strand=-1)
        else:
            location = FeatureLocation(start_position, end_position, strand=1)

        feature = SeqFeature(
            location=location,
            type=feature_type,
            qualifiers={
                "gene": row['Gene Name'],
                "product": row['Product'],
                "translation": row['Sequence'],
                "category": row['Category']
            }
        )
        record.features.append(feature)

    # Save the GenBank file
    with open(genbank_path, 'w') as output_file:
        SeqIO.write(record, output_file, "genbank")

    print(f"GenBank file has been saved to {genbank_path}")



from Bio import SeqIO, Entrez
from Bio.Seq import UndefinedSequenceError

Entrez.email = "hislam2@ur.rochester.edu"  # Replace with your actual email

'''def fetch_sequence_from_accession(accession_id):
    try:
        handle = Entrez.efetch(db="nucleotide", id=accession_id, rettype="fasta", retmode="text")
        record = SeqIO.read(handle, "fasta")
        handle.close()
        return str(record.seq), len(record.seq)
    except Exception as e:
        print(f"Error fetching sequence for {accession_id}: {e}")
        return "", 0'''

def get_length_from_metadata(record):
    try:
        contig_info = record.annotations["contig"]
        return int(contig_info.split("..")[-1])
    except (KeyError, ValueError):
        return "Unknown"



Entrez.email = "hislam2@ur.rochester.edu"  # Always set your email here

def fetch_sequence_from_accession(accession_id):
    
    try:
        handle = Entrez.efetch(db="nucleotide", id=accession_id, rettype="fasta", retmode="text")
        record = SeqIO.read(handle, "fasta")
        handle.close()
        return str(record.seq), len(record.seq)
    except Exception as e:
        print(f"Failed to fetch sequence for {accession_id} from NCBI: {e}")
        return "", 0  # Return empty sequence and length of 0 on failure

def get_sequence_length_from_header(file_path):
    
    try:
        with open(file_path, 'r') as f:
            for line in f:
                if line.startswith("LOCUS"):
                    parts = line.split()
                    return int(parts[2])  # The length is usually the third field
    except Exception as e:
        print(f"Failed to read sequence length from header: {e}")
    return 0

def extract_genbank_info(file_path):
    
    try:
        record = SeqIO.read(file_path, "genbank")
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return None, None, None
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return None, None, None

    # Extract CDS translations
    cds_translations = [
        feature.qualifiers.get("translation", [""])[0]
        for feature in record.features if feature.type == "CDS"
    ]

    # Handle missing or undefined sequence
    try:
        whole_nucleotide_sequence = str(record.seq)
        whole_sequence_length = len(record.seq)
    except UndefinedSequenceError:
        print(f"Sequence is undefined in the GenBank file: {file_path}. Attempting to fetch using accession ID.")

        # Try to fetch the sequence using the accession ID
        accession_id = record.id
        print(f"Fetching sequence for accession: {accession_id}")
        whole_nucleotide_sequence, whole_sequence_length = fetch_sequence_from_accession(accession_id)

        # If fetching fails, fallback to LOCUS line length
        if whole_sequence_length == 0:
            print(f"Failed to fetch sequence from NCBI. Falling back to LOCUS header length.")
            whole_sequence_length = get_sequence_length_from_header(file_path)
            whole_nucleotide_sequence = ""  # No sequence available

    return cds_translations, whole_nucleotide_sequence, whole_sequence_length


def editing_cds_list(CDS_list):
    filtered_list = [item for item in CDS_list if item]
    return filtered_list

import re
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord
from Bio import SeqIO
import os

def clean_sequence(sequence):
    # Convert to uppercase and remove any character that is not a valid DNA base
    return re.sub(r'[^ATCGN]', '', sequence.upper())

def save_fasta_file(plasmid, nucleotide_sequence):
    # Clean the nucleotide sequence
    cleaned_sequence = clean_sequence(nucleotide_sequence)
    
    # Create the SeqRecord object
    record = SeqRecord(Seq(cleaned_sequence), id=plasmid, description="")
    
    # Define the output file path
    fasta_file_path = os.path.join('tmp_files', plasmid + '.fasta')
    
    try:
        # Write the SeqRecord to a FASTA file
        with open(fasta_file_path, 'w') as output_handle:
            SeqIO.write(record, output_handle, "fasta")
        print(f"FASTA file successfully created: {fasta_file_path}")
    except Exception as e:
        print(f"Failed to write FASTA file: {e}")



def extract_cds_locations(contents):
    inside_cds = False
    cds_locations = []
    for line in contents:
        if line.startswith("     CDS             "):
            inside_cds = True
            location = line.split()[1]
            cds_locations.append(location)
        elif line.startswith("                     ") and inside_cds:
            # Continuation of feature location
            continuation = line.strip()
            cds_locations[-1] += continuation
        elif not line.startswith("                     ") and inside_cds:
            # No longer within a CDS feature
            inside_cds = False
    return cds_locations

def parse_cds_location_robust(location):
    # Extract numeric positions from the location string
    base_positions = re.findall(r"\d+\.\.\d+", location)
    ranges = []
    for pos in base_positions:
        start, end = map(int, pos.split('..'))
        # Ensure smaller number is first
        ranges.append((min(start, end), max(start, end)))
    
    # Handle the case where there might be no numeric positions found
    if not ranges:
        return None
    
    # If there's a join, we take the first start and the last end to get the complete range
    if "join" in location:
        start = ranges[0][0]
        end = ranges[-1][1]
        return (start, end)
    else:
        return ranges[0]

def getpositionsofCDS_genbank(file_path):
    import re
    # Load the contents of the GenBank file
    with open(file_path, "r") as file:
        contents = file.readlines()

    # Extract CDS feature locations from the file content
    cds_feature_locations = extract_cds_locations(contents)

    # Parse the locations and convert to tuples, filtering out None values
    parsed_locations = [parse_cds_location_robust(loc) for loc in cds_feature_locations if parse_cds_location_robust(loc) is not None]

    # Print or use the parsed locations
    #corrected_locations = [(min(start, end), max(start, end)) for start, end in parsed_locations]

    return parsed_locations

def complementpositions_genbank(file_path, positions):
    with open(file_path, "r") as file:
        contents = file.readlines()
    # Initialize the lists for complement start and end
    complement_start = []
    complement_end = []
    corrected_locations =positions;
    for start, end in corrected_locations:
        # Check for the start position
        for line in contents:
            if f"{start}" in line and "complement" in line:
                complement_start.append(start)
                break  # No need to check further for this start position

        # Check for the end position
        for line in contents:
            if f"{end}" in line and "complement" in line:
                complement_end.append(end)
                break  # No need to check further for this end position
    # Remove duplicates while preserving order manually
    def remove_duplicates_preserve_order(sequence):
        seen = set()
        return [x for x in sequence if not (x in seen or seen.add(x))]

    complement_start = remove_duplicates_preserve_order(complement_start)
    complement_end = remove_duplicates_preserve_order(complement_end)
    # Save the complement start positions to a text file
    with open("tmp_files/complementstarting.txt", "w") as start_file:
        start_file.write("\n".join(str(complement_start)))

    # Save the complement end positions to a text file
    with open("tmp_files/complementending.txt", "w") as end_file:
        end_file.write("\n".join(str(complement_end)))
    # Display the results
    return complement_start, complement_end




import os
from Bio.Blast import NCBIXML
from concurrent.futures import ProcessPoolExecutor
import pandas as pd

def run_blast_genbank(sequence, index, list_of_positions):
    query_path = f'tmp_files/query_{index}.fsa'
    result_path = f'tmp_files/result_{index}.xml'
    
    # Write the sequence to a temporary FASTA file
    with open(query_path, 'w') as query_file:
        query_file.write(f'>Coding Sequence{index}\n{sequence}')

    # Check if the sequence is actually written to the file
    if os.stat(query_path).st_size == 0:
        #print(f'Query file {query_path} is empty. No sequence data available for BLAST.')
        return []
    
    # Run BLAST
    command = f'blastp -query {query_path} -db makedb_folder/blastdb/custom_database -outfmt 5 -out {result_path}'
    exit_code = os.system(command)
    if exit_code != 0:
        #print(f'BLAST command failed for query file {query_path}. Exit code: {exit_code}')
        return []

    # Parse BLAST result
    try:
        with open(result_path, 'r') as result_file:
            records = NCBIXML.parse(result_file)
            item = next(records)
            results = []
            for alignment in item.alignments:
                for hsp in alignment.hsps:
                    if hsp.expect < 0.001 and hsp.identities / alignment.length * 100 > 60:
                        results.append({
                            "Name of Query": f"Coding Sequence{index}",
                            "Start Position": list_of_positions[index][0],
                            "End Position": list_of_positions[index][1],
                            "Title": alignment.title.split(' ')[1],
                            "Length": alignment.length,
                            "Score": hsp.score,
                            "Pident": hsp.identities / alignment.length * 100,
                            "Gaps": hsp.gaps,
                            "E-value": hsp.expect,
                            "Sequence": hsp.query,
                            "Query Length": len(sequence),
                            "Subject Length": alignment.length
                        })
            #if not results:
                #print(f'No valid BLAST hits for query file {query_path}.')
            return results
    except Exception as e:
        #print(f'Failed to parse BLAST results for {query_path}: {e}')
        return []

def select_gene_row_genbank(df):
    # First try to filter rows with 'Percent Identity' = 100
    filtered_df = df[df['Pident'] >= 75]
    
    # If no rows with 100% identity, or less than 10 rows with 100% identity, consider rows with 'Percent Identity' > 90%
    #if filtered_df.empty or len(filtered_df) < 5:
    if filtered_df.empty:
        filtered_df = df[df['Pident'] > 60]
    
    # Count the occurrences of each gene
    gene_counts = filtered_df['Gene Name'].value_counts()
    max_occurrence = gene_counts.max()
    # Identify genes with the maximum occurrence
    most_frequent_genes = gene_counts[gene_counts == max_occurrence].index.tolist()
    # Filter for the most frequent genes
    most_frequent_df = filtered_df[filtered_df['Gene Name'].isin(most_frequent_genes)]
    # Select the row with the lowest E-value for each gene
    selected_rows = most_frequent_df.loc[most_frequent_df.groupby('Gene Name')['E-value'].idxmin()]
    return selected_rows



def initial_blast_against_database_genbank(list_of_cds, list_of_positions, database_path):
    # Assuming database is loaded from a CSV or similar file
    database = pd.read_csv(database_path)

    with ProcessPoolExecutor() as executor:
        futures = [executor.submit(run_blast_genbank, seq, idx, list_of_positions) for idx, seq in enumerate(list_of_cds)]
        results = [future.result() for future in futures]

    # Flatten list of lists
    flat_results = [item for sublist in results for item in sublist]
    
    # Create DataFrame from results
    final_dataframe = pd.DataFrame(flat_results)
    if not final_dataframe.empty:
        final_dataframe['Gene Name'], final_dataframe['index'] = zip(*final_dataframe['Title'].apply(extract_gene_info))
        final_dataframe.dropna(subset=['Gene Name', 'index'], inplace=True)
        
        # Further processing
        unique_query_names = final_dataframe['Name of Query'].unique()
        selected_rows_per_query = pd.concat([select_gene_row_genbank(final_dataframe[final_dataframe['Name of Query'] == query_name]) for query_name in unique_query_names])
        selected_rows_per_query.reset_index(drop=True, inplace=True)
        
        # Append product and category information
        # Ensure index is integer and within the range
        selected_rows_per_query['Category'] = [database['Category'].iloc[int(index)] if int(index) < len(database) else None for index in selected_rows_per_query['index']]
        selected_rows_per_query['Product'] = [database['Product'].iloc[int(index)] if int(index) < len(database) else None for index in selected_rows_per_query['index']]
        
        # Clean up DataFrame
        selected_rows_per_query.drop(['index', 'Title', 'Pident', 'Query Length', 'Subject Length'], axis=1, inplace=True)

    return selected_rows_per_query

def process_final_dataframe_genbank(selected_rows_per_query, replicon_dataframe, oric_dataframe, orit_dataframe, transposon):
    merged_df = pd.concat([selected_rows_per_query, replicon_dataframe, oric_dataframe, orit_dataframe, transposon], ignore_index=True)
    columns = ['index']
    merged_df.drop(columns, inplace=True, axis=1)
    df_dedup = merged_df.loc[merged_df.groupby('Name of Query')['E-value'].idxmin()]
    df_dedup['Start Position'] = df_dedup['Start Position'].astype(int)
    df_dedup['Endt Position'] = df_dedup['End Position'].astype(int)
    sorted_df = df_dedup.sort_values(by='Start Position')
    return sorted_df

def remove_contained_rows(df):
    indices_to_drop = []
    current_start = -1
    current_end = -1
    
    for index, row in df.iterrows():
        if row['Start Position'] >= current_start and row['End Position'] <= current_end:
            indices_to_drop.append(index)
        else:
            current_start = row['Start Position']
            current_end = row['End Position']
    
    return df.drop(indices_to_drop)


def filter_close_sequences(df, threshold=100):
    # Convert columns to numeric if they are not already
    df['Start Position'] = pd.to_numeric(df['Start Position'], errors='coerce')
    df['End Position'] = pd.to_numeric(df['End Position'], errors='coerce')

    # Sort DataFrame by 'Start Position'
    df = df.sort_values(by='Start Position')

    to_keep = []
    last_start = -1
    last_end = -1

    for index, row in df.iterrows():
        # Initialize the first sequence to keep
        if last_start == -1 and last_end == -1:
            last_start = row['Start Position']
            last_end = row['End Position']
            to_keep.append(index)
        else:
            # Keep sequences that are not within the 'threshold' distance from the last kept sequence
            if (abs(row['Start Position'] - last_start) > threshold) and (abs(row['End Position'] - last_end) > threshold):
                last_start = row['Start Position']
                last_end = row['End Position']
                to_keep.append(index)

    return df.loc[to_keep]


def remove_overlapping_transposons(transposon_df):
    # Sort transposons by start position, then by end position to prioritize earlier starts
    transposon_df = transposon_df.sort_values(by=['Start Position', 'End Position'])
    valid_indices = []
    current_end = -1
    
    for index, row in transposon_df.iterrows():
        if row['Start Position'] > current_end:
            # If the current transposon starts after the end of the last kept transposon, keep it
            valid_indices.append(index)
            current_end = row['End Position']
            
    return transposon_df.loc[valid_indices]

def retain_transposons_with_overlap(transposon_df, resistance_df):
    valid_indices = []
    for index, transposon in transposon_df.iterrows():
        for _, resistance in resistance_df.iterrows():
            # Check full containment of transposon within resistance range
            if transposon['Start Position'] >= resistance['Start Position'] and transposon['End Position'] <= resistance['End Position']:
                valid_indices.append(index)
                break
            # Check partial overlap of resistance within transposon range
            elif (resistance['Start Position'] >= transposon['Start Position'] and resistance['Start Position'] <= transposon['End Position']) or \
                 (resistance['End Position'] >= transposon['Start Position'] and resistance['End Position'] <= transposon['End Position']):
                valid_indices.append(index)
                break
    return transposon_df.loc[valid_indices]



def filter_close_sequences_cds(df, threshold=10):
    # Convert 'Start Position' and 'End Position' to numeric types
    df['Start Position'] = pd.to_numeric(df['Start Position'], errors='coerce')
    df['End Position'] = pd.to_numeric(df['End Position'], errors='coerce')
    
    # Sort DataFrame by 'Start Position'
    df = df.sort_values(by='Start Position')
    to_keep = []
    last_start = -1
    last_end = -1

    for index, row in df.iterrows():
        # Initialize the first sequence to keep
        if last_start == -1 and last_end == -1:
            last_start = row['Start Position']
            last_end = row['End Position']
            to_keep.append(index)
        else:
            # Check if the current row's start and end positions are beyond the threshold distance from the last kept sequence
            if (abs(row['Start Position'] - last_start) > threshold) and (abs(row['End Position'] - last_end) > threshold):
                last_start = row['Start Position']
                last_end = row['End Position']
                to_keep.append(index)

    return df.loc[to_keep]



def merge_all_ther_database_and_fix_accordingly(main, oric,orit, transposon, replicon):
    main  = filter_close_sequences_cds( main)
    replicon = filter_close_sequences(replicon)
    oric_df_adjusted = oric.rename(columns={
    'Query Name': 'Name of Query',
    'Gene Name': 'Gene Name',
    'Length': 'Length',
    'Score': 'Score',
    'Gaps': 'Gaps',
    'E-value': 'E-value',
    'Sequence': 'Sequence',
    'Start Position': 'Start Position',
    'End Position': 'End Position',
    'Product': 'Product'})
    oric_df_unique = oric_df_adjusted.drop_duplicates(subset=['Start Position', 'End Position'], keep='first')
    oric_df_unique.reset_index(drop=True, inplace=True)
    oric_df_unique['Category']='Origin of Replication'

    orit_df_adjusted = orit.rename(columns={
    'Query Name': 'Name of Query',
    'Gene Name': 'Gene Name',
    'Length': 'Length',
    'Score': 'Score',
    'Gaps': 'Gaps',
    'E-value': 'E-value',
    'Sequence': 'Sequence',
    'Start Position': 'Start Position',
    'End Position': 'End Position',
    'Product': 'Product'})
    orit_df_unique = orit_df_adjusted.drop_duplicates(subset=['Start Position', 'End Position'], keep='first')
    orit_df_unique.reset_index(drop=True, inplace=True)
    orit_df_unique['Category']='Origin of Transfer'

    transposon_df_adjusted = transposon.rename(columns={
        'Query Name': 'Name of Query',
        'Gene Name': 'Gene Name',
        'Length': 'Length',
        'Score': 'Score',
        'Gaps': 'Gaps',
        'E-value': 'E-value',
        'Sequence': 'Sequence',
        'Start Position': 'Start Position',
        'End Position': 'End Position',
        'Product': 'Product'
    })
    transposon_df_unique = transposon_df_adjusted.drop_duplicates(subset=['Start Position', 'End Position'], keep='first')
    transposon_df_unique .reset_index(drop=True, inplace=True)
    transposon_df_unique ['Category']='Transposable Element'

    complete_df = pd.concat([main, oric_df_unique, orit_df_unique,replicon, transposon_df_unique], ignore_index=True)

    total_df=complete_df


    # Apply containment removal for OriC and Orit sequences
    oric_sequences = total_df[total_df['Name of Query'].str.contains("OriC Sequence")]
    oric_sequences_filtered = remove_contained_rows(oric_sequences)
    orit_sequences = total_df[total_df['Name of Query'].str.contains("Orit Sequence")]
    orit_sequences_filtered = remove_contained_rows(orit_sequences)

    # Filter closely spaced sequences for OriC and Orit
    oric_final = filter_close_sequences(oric_sequences_filtered)
    orit_final = filter_close_sequences(orit_sequences_filtered)

    # Remove original entries and append filtered data
    total_df_cleaned = total_df.drop(total_df[total_df['Name of Query'].str.contains("OriC Sequence|Orit Sequence")].index)
    total_df_final = pd.concat([total_df_cleaned, oric_final, orit_final], ignore_index=True)

    cleaned_data=total_df_final
    transposon_sequences = cleaned_data[cleaned_data['Name of Query'].str.contains("transposon Sequence")]
    antibiotic_resistance_rows = cleaned_data[cleaned_data['Category'] == 'Antibiotic Resistance']

    # Remove overlapping transposon sequences
    non_overlapping_transposons = remove_overlapping_transposons(transposon_sequences)

    # Retain relevant transposon sequences based on overlap with antibiotic resistance genes
    retained_transposons = retain_transposons_with_overlap(non_overlapping_transposons, antibiotic_resistance_rows)

    # Remove original transposon entries from the cleaned data and replace with filtered ones
    final_cleaned_data = cleaned_data[~cleaned_data['Name of Query'].str.contains("transposon Sequence")]
    final_cleaned_data = pd.concat([final_cleaned_data, retained_transposons], ignore_index=True)

    return final_cleaned_data





def make_genbank_file_for_retaining_cds(only_sequence, final_df, genbank_path, plasmid,complement_starts, complement_ends):
    # Read complement start and end positions from the text files

    # Handle None sequence by providing an empty string
    sequence_data = '' if only_sequence is None else only_sequence

    record = SeqRecord(
        Seq(sequence_data),  # Initialize with a sequence or an empty string
        id="00000",
        name=plasmid,
        description="Genbank file for Plasmid " + plasmid,
        annotations={"molecule_type": "DNA"}  # Specify the molecule type
    )

    final_df['Start Position'] = pd.to_numeric(final_df['Start Position'], errors='coerce').fillna(0).astype(int)
    final_df['End Position'] = pd.to_numeric(final_df['End Position'], errors='coerce').fillna(0).astype(int)

    # Function to determine if a position is complement
    def is_complement(start, end, comp_starts, comp_ends):
        return start in comp_starts and end in comp_ends

    def determine_feature_type(category):
        if category == "Transposable Element":
            return "MGE"
        elif category == "Origin of Transfer":
            return "OriT"
        elif category == "Origin of Replication":
            return "OriC"
        elif category == "Replicon":
            return "Replicon"
        else:
            return "CDS"  # Default feature type

    # Add features to the GenBank record
    for idx, row in final_df.iterrows():
        feature_type = determine_feature_type(row['Category'])

        start_position = row['Start Position'] - 1
        end_position = row['End Position']

        # Check if the end position is greater than or equal to the start position
        if end_position < start_position:
            print(f"Skipping invalid feature with start {start_position + 1} and end {end_position}")
            continue

        # Determine if the feature is on the complement strand
        if is_complement(row['Start Position'], row['End Position'], complement_starts, complement_ends):
            location = FeatureLocation(start_position, end_position, strand=-1)
        else:
            location = FeatureLocation(start_position, end_position, strand=1)

        feature = SeqFeature(
            location=location,
            type=feature_type,
            qualifiers={
                "gene": row['Gene Name'],
                "product": row['Product'],
                "translation": row['Sequence'],
                "category": row['Category']
            }
        )
        record.features.append(feature)

    # Save the GenBank file
    with open(genbank_path, 'w') as output_file:
        SeqIO.write(record, output_file, "genbank")

    print(f"GenBank file has been saved to {genbank_path}")



def make_genbank_file_for_overwriting_cds_no_seq(length, final_df, genbank_path, plasmid, complement_starts, complement_ends):
    # Use a placeholder sequence of "N" * length
    placeholder_sequence = "N" * length

    record = SeqRecord(
        Seq(placeholder_sequence),  # Placeholder sequence of "N"
        id="00000",
        name=plasmid,
        description="GenBank file for Plasmid " + plasmid,
        annotations={"molecule_type": "DNA"}  # Specify the molecule type
    )
    
    # Convert start and end positions to numeric and handle invalid entries
    final_df['Start Position'] = pd.to_numeric(final_df['Start Position'], errors='coerce').fillna(0).astype(int)
    final_df['End Position'] = pd.to_numeric(final_df['End Position'], errors='coerce').fillna(0).astype(int)

    # Function to determine if a position is complement
    def is_complement(start, end, comp_starts, comp_ends):
        return start in comp_starts and end in comp_ends

    # Function to determine feature type
    def determine_feature_type(category):
        if category == "Transposable Element":
            return "MGE"
        elif category == "Origin of Transfer":
            return "OriT"
        elif category == "Origin of Replication":
            return "OriC"
        elif category == "Replicon":
            return "Replicon"
        else:
            return "CDS"  # Default feature type

    # Add features to the GenBank record
    for idx, row in final_df.iterrows():
        feature_type = determine_feature_type(row['Category'])

        start_position = row['Start Position'] - 1
        end_position = row['End Position']

        # Check if the end position is greater than or equal to the start position
        if end_position < start_position:
            print(f"Skipping invalid feature with start {start_position + 1} and end {end_position}")
            continue

        # Determine if the feature is on the complement strand
        if is_complement(row['Start Position'], row['End Position'], complement_starts, complement_ends):
            location = FeatureLocation(start_position, end_position, strand=-1)
        else:
            location = FeatureLocation(start_position, end_position, strand=1)

        feature = SeqFeature(
            location=location,
            type=feature_type,
            qualifiers={
                "gene": row['Gene Name'],
                "product": row['Product'],
                "translation": row['Sequence'],
                "category": row['Category']
            }
        )
        record.features.append(feature)

    # Write the GenBank file with the placeholder sequence
    with open(genbank_path, 'w') as output_file:
        SeqIO.write(record, output_file, "genbank")

    print(f"GenBank file has been saved to {genbank_path}")

from datetime import datetime

def fix_genbank_date(file_path):
    today_date = datetime.now().strftime("%d-%b-%Y").upper()
    updated_lines = []

    # Read the file and modify the LOCUS line
    with open(file_path, 'r') as file:
        lines = file.readlines()

    for i, line in enumerate(lines):
        if i == 0:  # LOCUS line
            # Parse the existing LOCUS line and reconstruct it with circular and updated date
            parts = line.split()
            # Ensure the LOCUS line includes the correct fields and formatting
            locus_line = (
                f"LOCUS       {parts[1]:<16}"  # Name field
                f"{parts[2]:>11} bp    "    # Length field
                f"DNA     circular   "       # Molecule type and shape
                f"BCT {today_date}\n"        # Dataclass and date
            )
            updated_lines.append(locus_line)
        else:
            updated_lines.append(line)

    # Write the updated file back
    with open(file_path, 'w') as file:
        file.writelines(updated_lines)


