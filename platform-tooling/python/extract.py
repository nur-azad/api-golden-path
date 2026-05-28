import re
import yaml
import json

# Define inputs and outputs
input_file = 'traffic.har'
output_file = 'extracted_openapi.yaml'

try:
    with open(input_file, 'r', encoding='utf-8', errors='ignore') as f:
        log_data = f.read()
except FileNotFoundError:
    # Fallback to literal text structure string if file handles aren't ready yet
    log_data = """YOUR_LOG_STRING_HERE"""

# Find individual transaction sequences using mitmproxy chunk offsets
# Splitting on websocket/response boundaries isolates individual network exchanges
sessions = re.split(r'\d+:9:websocket;', log_data)

paths = {}

for session in sessions:
    if not session.strip():
        continue
        
    # Isolate the exact HTTP Method verb and route Path strings
    method_match = re.search(r'method;\d+:([A-Z]+)', session)
    path_match = re.search(r'path;\d+:(/[^\s,;#}]+)', session)
    status_match = re.search(r'status_code;\d+:(\d+)', session)
    
    if path_match and method_match:
        raw_path = path_match.group(1)
        method = method_match.group(1).lower()
        status = status_match.group(1) if status_match else "200"
        
        # We exclusively process custom application routes matching /api/
        if '/api/' in raw_path:
            clean_path = '/api/' + raw_path.split('/api/')[-1].split('?')[0]
            
            # Initialize specification dictionary structures
            if clean_path not in paths:
                paths[clean_path] = {}
            if method not in paths[clean_path]:
                paths[clean_path][method] = {
                    'summary': f'Extracted legacy {method.upper()} endpoint',
                    'responses': {}
                }
            
            # Use the mitmproxy length prefix (content;N:...) to extract exact bytes — avoids
            # non-greedy regex stopping early inside nested JSON structures
            content_match = re.search(r'content;(\d+):([\[\{])', session)
            schema_node = {"type": "object"}

            # Map Python runtime types to valid OpenAPI/JSON Schema type names
            TYPE_MAP = {
                "int": "integer", "float": "number", "str": "string",
                "bool": "boolean", "dict": "object", "list": "array", "NoneType": "string"
            }

            if content_match:
                length = int(content_match.group(1))
                start = content_match.start(2)
                content_str = session[start:start + length]
                try:
                    parsed_json = json.loads(content_str)
                    if isinstance(parsed_json, list) and len(parsed_json) > 0:
                        sample = parsed_json[0]
                        schema_node = {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {k: {"type": TYPE_MAP.get(type(v).__name__, "string")} for k, v in sample.items()}
                            }
                        }
                    elif isinstance(parsed_json, dict):
                        schema_node = {
                            "type": "object",
                            "properties": {k: {"type": TYPE_MAP.get(type(v).__name__, "string")} for k, v in parsed_json.items()}
                        }
                except Exception:
                    pass  # Keep default placeholder if content is not parseable JSON
            
            # Mount response criteria
            paths[clean_path][method]['responses'][status] = {
                'description': f'Detected status {status} response transaction.',
                'content': {
                    'application/json': {
                        'schema': schema_node
                    }
                }
            }

# Build structured specification template compliant with OpenAPI 3.0.3
openapi_spec = {
    'openapi': '3.0.3',
    'info': {
        'title': 'Extracted Legacy Orders API',
        'description': 'Reverse-engineered OpenAPI document constructed from mitmproxy transaction traces.',
        'version': '1.0.0'
    },
    'paths': paths
}

with open(output_file, 'w', encoding='utf-8') as out:
    yaml.dump(openapi_spec, out, default_flow_style=False, sort_keys=False)

print(f"Success! Generated '{output_file}' with response schemas from network logs.")
