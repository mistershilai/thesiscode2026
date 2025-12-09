import requests

# one warehouse coordinate (Francistown area)
start = (26.824311, -23.115351)
# one facility coordinate (Gaborone area)
end = (25.920000, -24.680000)

url = f"http://localhost:5001/route/v1/driving/{start[0]},{start[1]};{end[0]},{end[1]}?overview=false"
print("Querying:", url)

r = requests.get(url)
print("Status code:", r.status_code)
print("Response:", r.text[:500])
