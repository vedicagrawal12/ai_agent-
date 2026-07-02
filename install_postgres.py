import zipfile
import tarfile
import os

jar_file = "postgres_embedded.jar"

print("Extracting JAR...")
with zipfile.ZipFile(jar_file, 'r') as z:
    z.extract("postgres-windows-x86_64.txz", ".")

print("Extracting TXZ...")
with tarfile.open("postgres-windows-x86_64.txz", "r:xz") as t:
    t.extractall("pgsql")

print("PostgreSQL binaries extracted to ./pgsql")

# Clean up
os.remove(jar_file)
os.remove("postgres-windows-x86_64.txz")
print("Done.")
