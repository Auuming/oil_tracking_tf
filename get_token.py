import sys
import json
import urllib.request
import urllib.parse
import base64
import time

def main():
    # 1. Read the DB credentials passed by OpenTofu
    input_data = json.load(sys.stdin)
    url = input_data['url'].rstrip('/')
    username = input_data['username']
    password = input_data['password']
    org = input_data['org']

    auth_str = f"{username}:{password}"
    b64_auth = base64.b64encode(auth_str.encode('utf-8')).decode('utf-8')
    
    # 2. Retry loop in case the DB is still booting up during tofu apply
    for attempt in range(5):
        try:
            # A. Sign in to get a temporary Session Cookie
            req1 = urllib.request.Request(f"{url}/api/v2/signin", method="POST")
            req1.add_header("Authorization", f"Basic {b64_auth}")
            resp1 = urllib.request.urlopen(req1, timeout=10)
            cookie = resp1.headers.get('Set-Cookie')

            # B. Get your Organization ID
            req2 = urllib.request.Request(f"{url}/api/v2/orgs?org={urllib.parse.quote(org)}")
            req2.add_header("Cookie", cookie)
            resp2 = urllib.request.urlopen(req2, timeout=10)
            org_id = json.loads(resp2.read())['orgs'][0]['id']
            
            # C. Find and Delete old tokens created by OpenTofu (prevents infinite clutter)
            req_list = urllib.request.Request(f"{url}/api/v2/authorizations")
            req_list.add_header("Cookie", cookie)
            resp_list = urllib.request.urlopen(req_list, timeout=10)
            existing_auths = json.loads(resp_list.read()).get('authorizations', [])
            
            for auth in existing_auths:
                if auth.get('description') == "OpenTofu Auto-Generated Token":
                    req_del = urllib.request.Request(f"{url}/api/v2/authorizations/{auth['id']}", method="DELETE")
                    req_del.add_header("Cookie", cookie)
                    urllib.request.urlopen(req_del, timeout=10)

            # D. Create the new API Token for your Lambdas
            payload = {
                "orgID": org_id,
                "description": "OpenTofu Auto-Generated Token",
                "permissions": [
                    {"action": "read", "resource": {"type": "buckets"}},
                    {"action": "write", "resource": {"type": "buckets"}}
                ]
            }
            req3 = urllib.request.Request(f"{url}/api/v2/authorizations", data=json.dumps(payload).encode('utf-8'), method="POST")
            req3.add_header("Cookie", cookie)
            req3.add_header("Content-Type", "application/json")
            resp3 = urllib.request.urlopen(req3, timeout=10)
            token = json.loads(resp3.read())['token']

            # E. Pass the token back to OpenTofu as JSON!
            print(json.dumps({"token": token}))
            return

        except Exception as e:
            time.sleep(10) # Wait and retry if DB isn't fully ready yet

    print(json.dumps({"error": "Failed to connect and get token"}), file=sys.stderr)
    sys.exit(1)

if __name__ == "__main__":
    main()