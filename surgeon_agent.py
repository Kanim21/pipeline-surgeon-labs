import re
import os
import requests

def get_maven_coordinates(package_name):
    url = f"https://search.maven.org/solrsearch/select?q=fc:%22{package_name}%22&rows=1&wt=json"
    response = requests.get(url).json()
    docs = response.get('response', {}).get('docs', [])
    if docs:
        g, a, v = docs[0]['g'], docs[0]['a'], docs[0]['v']
        return f"""
    <dependency>
      <groupId>{g}</groupId>
      <artifactId>{a}</artifactId>
      <version>{v}</version>
    </dependency>"""
    return None

def heal_pipeline():
    log_path = "maven_output.log"
    pom_path = "pom.xml"

    if not os.path.exists(log_path): return
    with open(log_path, 'r') as f: logs = f.read()

    match = re.search(r"package ([\w\.]+) does not exist", logs)
    if match:
        pkg = match.group(1)
        print(f"DIAGNOSIS: Missing {pkg}. Consulting Maven Central...")
        snippet = get_maven_coordinates(pkg)
        
        if snippet:
            with open(pom_path, 'r') as f: pom = f.read()
            if "</dependencies>" in pom:
                new_pom = pom.replace("</dependencies>", f"  {snippet}\n  </dependencies>")
            else:
                new_pom = pom.replace("</project>", f"  <dependencies>\n  {snippet}\n  </dependencies>\n</project>")
            
            with open(pom_path, 'w') as f: f.write(new_pom)
            print("SURGERY SUCCESSFUL: Dependency injected.")
        else:
            print("ERROR: Could not find package coordinates.")

if __name__ == "__main__":
    heal_pipeline()
