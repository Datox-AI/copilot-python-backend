import subprocess

# Define the command to be executed
command = [
    "openssl",
    "req",
    "-newkey", "rsa:2048",
    "-nodes",
    "-keyout", "domain.key",
    "-out", "domain.csr"
]

# Run the command
process = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

# Check if the command was successful
if process.returncode == 0:
    print("SSL key and CSR generated successfully.")
    print(process.stdout)
else:
    print("Error in generating SSL key and CSR.")
    print(process.stderr)
