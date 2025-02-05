import os
import subprocess as sp

def run_pipeline(input_file, output_folder):
    """
    Runs the plasmid annotation pipeline by calling annotate_plasmid.py
    - input_file: Path to the uploaded FASTA/GenBank file
    - output_folder: Folder to save results
    Returns: Filenames of PNG, CSV, and GBK
    """

    # Ensure output directory exists
    os.makedirs(output_folder, exist_ok=True)

    # Determine file type based on extension
    file_extension = os.path.splitext(input_file)[1].lower()
    if file_extension in ['.fasta', '.fa', '.fna']:
        file_type = "fasta"
    elif file_extension in ['.gb', '.gbk', '.genbank']:
        file_type = "genbank"
    else:
        raise ValueError("Unsupported file format. Please upload a FASTA or GenBank file.")

    # Define expected output filenames
    base_name = os.path.basename(input_file).split('.')[0]
    output_csv = os.path.join(output_folder, f"{base_name}_results.csv")
    output_gbk = os.path.join(output_folder, f"{base_name}_annotated.gbk")
    output_png = os.path.join(output_folder, f"{base_name}_map.png")

    # Run annotate_plasmid.py using subprocess with correct file type flag
    annotation_command = f"python annotate_plasmid.py -i {input_file} -o {output_folder} -t {file_type}"
    sp.run(annotation_command, shell=True, check=True)

    # Return result filenames
    return output_png, output_csv, output_gbk
