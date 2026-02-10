from sodapy import Socrata

# Initialize client
client = Socrata("www.dallasopendata.com", "ugOmFkrzJOT3LnEf6MoYIwx15")

# Get metadata for Police Incidents dataset
metadata = client.get_metadata("qv6i-rri7")

print(f"Total Columns: {len(metadata['columns'])}\n")
print("Date/Time related columns:")
print("-" * 60)

for col in metadata['columns']:
    name = col.get('name', '')
    field = col.get('fieldName', '')
    dtype = col.get('dataTypeName', '')
    
    # Check if it's a date/time column
    if ('date' in name.lower() or 'time' in name.lower() or 
        dtype in ['calendar_date', 'floating_timestamp']):
        print(f"  Field: {field}")
        print(f"  Name: {name}")
        print(f"  Type: {dtype}")
        print()

client.close()
