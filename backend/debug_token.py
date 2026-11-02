import base64

token = "eyJhbGciOiJFUzI1NiIsImtpZCI6Ijg5NDljYWNlLThkYmYtNGU3YS04NmM2LWE3ZDA5ODY3MDc2ZiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJodHRwczovL2NweXRwcmV3bndlZml1ZmVnZ3F0LnN1cGFiYXNlLmNvL2F1dG8vMjEiLCJzdWIiOiJhMmQzYWQxOC1lOTFkLTQ2MjItODU5My0xMDYyMDY1MGZlZDQiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzg1OTM5NjQ5LCJpYXQiOjE3ODU5MzYwNDksImVtYWlsIjoiY2VvQHRlc3QuZW55LmRldiIsInBob25lIjoiIiwiYXBwX21ldGFkYXRhIjp7InByb3ZpZGVyIjoiZW1haWwiLCJwcm92aWRlcnMiOlsiZW1haWwiXX0sInVzZXJfbWV0YWRhdGEiOnsiZW1haWxfdmVyaWZpZWQiOnRydWUsInJvbGVzIjpbImNlbyJdLCJyb2xlIjoiYXV0aGVudGljYWVkIiwiYWFsIjoiYWFsMSIsImFtcCI6W3sidGVybSI6InBhc3N3b3JkIiwidGltZXN0YW1wIjoxNzg1OTM2MDQ4fV0sInNlc3Npb25faWQiOiIyOWQ0YmJlLTRiZDYtNDM2Zi1iYmJhLTI5ZmQxMjJlNzE0MiIsImlzX2Fub25tb3VzIjpmYWxzZX0.Csk-8MOjnUyQZ2j0IrQSfxxeet0K0IRjtWweZ6CL-numlKOBmoQYU1M-Hyj-1Z8hot8fseH3FsTylHx1HM9dZA"
parts = token.split('.')
if len(parts) == 3:
    header_b64, payload_b64, sig_b64 = parts
    print(f"payload_b64: {payload_b64}")
    # Add padding if needed
    payload_b64_padded = payload_b64
    if len(payload_b64) % 4:
        payload_b64_padded += '=' * (4 - len(payload_b64) % 4)
    try:
        decoded_bytes = base64.b64decode(payload_b64_padded)
        print(f"Decoded bytes: {decoded_bytes}")
        print(f"Decoded string: {decoded_bytes.decode('utf-8')}")
    except Exception as e:
        print(f"Error decoding base64: {e}")
else:
    print("Invalid token")