import re
import argparse

def parse_ini_string(data):
    regex = {
        'section': re.compile(r'^\s*\[\s*([^\]]*)\s*\]\s*$'),
        'param': re.compile(r'^\s*([^=]+?)\s*=\s*(.*?)\s*$'),
        'comment': re.compile(r'^\s*;.*$')
    }
    value = {}
    lines = data.split('\n')
    section = None
    for line in lines:
        if regex['comment'].match(line):
            continue
        elif regex['param'].match(line):
            match = regex['param'].match(line)
            if section:
                value.setdefault(section, {})[match.group(1)] = match.group(2)
            else:
                value[match.group(1)] = match.group(2)
        elif regex['section'].match(line):
            match = regex['section'].match(line)
            value[match.group(1)] = {}
            section = match.group(1)
        elif not line.strip() and section:
            section = None
    return value

def parse_environment(raw):
    parts = re.findall(r'\S+|"[^"]+"', raw)
    result = {}
    for part in parts:
        key, value = part.split('=', 1)
        result[key] = value.strip('"')
    return result

def validate(parsed):
    if 'Service' not in parsed:
        return "No [Service] section found"

    if 'EnvironmentFile' in parsed['Service']:
        return "Environment= is not supported in openrc"

    return None

def unit_to_rc(name):
    table = {
        "network.target": "net",
        "remote-fs.target": "netmount",
        "nss-lookup.target": "dns"
    }
    if name in table:
        return table[name]
    else:
        return name.split('.')[0]

def units_to_rc(units):
    names = units.split()
    return ' '.join(unit_to_rc(name) for name in names)

def generate_depend(unit):
    depend = ""
    if 'After' in unit['Unit']:
        depend += f"\tafter {units_to_rc(unit['Unit']['After'])}\n"
    if 'Before' in unit['Unit']:
        depend += f"\tbefore {units_to_rc(unit['Unit']['Before'])}\n"
    if 'Requires' in unit['Unit']:
        depend += f"\tneed {units_to_rc(unit['Unit']['Requires'])}\n"
    if 'Wants' in unit['Unit']:
        depend += f"\tuse {units_to_rc(unit['Unit']['Wants'])}\n"

    if depend:
        return f"\ndepend() {{\n{depend}}}\n"
    return ""

def generate_supervise_args(unit):
    result = ""
    if 'WorkingDirectory' in unit['Service']:
        result += f" -d {unit['Service']['WorkingDirectory']}"
    if 'RootDirectory' in unit['Service']:
        result += f" -r {unit['Service']['RootDirectory']}"
    if 'UMask' in unit['Service']:
        result += f" -k {unit['Service']['UMask']}"
    if 'Nice' in unit['Service']:
        result += f" -N {unit['Service']['Nice']}"
    if 'IOSchedulingClass' in unit['Service']:
        if 'IOSchedulingPriority' in unit['Service']:
            result += f" -I {unit['Service']['IOSchedulingClass']}:{unit['Service']['IOSchedulingPriority']}"
        else:
            result += f" -I {unit['Service']['IOSchedulingClass']}"
    if 'StandardOutput' in unit['Service']:
        if unit['Service']['StandardOutput'].startswith('file:'):
            result += f" -1 {unit['Service']['StandardOutput'][5:]}"
            if 'StandardError' not in unit['Service']:
                unit['Service']['StandardError'] = unit['Service']['StandardOutput']
    if 'StandardError' in unit['Service']:
        if unit['Service']['StandardError'].startswith('file:'):
            result += f" -2 {unit['Service']['StandardError'][5:]}"
    if 'Environment' in unit['Service']:
        env = parse_environment(unit['Service']['Environment'])
        for key, value in env.items():
            result += f" -e {key}=\"{value}\""

    if result:
        return 'supervise_daemon_args="' + result.strip() + '"\n'
    else:
        return ''

def generate_ssd_args(unit):
    result = ""
    if 'WorkingDirectory' in unit['Service']:
        result += f" -d {unit['Service']['WorkingDirectory']}"
    if 'RootDirectory' in unit['Service']:
        result += f" -r {unit['Service']['RootDirectory']}"
    if 'UMask' in unit['Service']:
        result += f" -k {unit['Service']['UMask']}"
    if 'Nice' in unit['Service']:
        result += f" -N {unit['Service']['Nice']}"
    if 'IOSchedulingClass' in unit['Service']:
        if 'IOSchedulingPriority' in unit['Service']:
            result += f" -I {unit['Service']['IOSchedulingClass']}:{unit['Service']['IOSchedulingPriority']}"
        else:
            result += f" -I {unit['Service']['IOSchedulingClass']}"
    if 'CPUSchedulingPolicy' in unit['Service']:
        if 'CPUSchedulingPriority' in unit['Service']:
            result += f" -I {unit['Service']['CPUSchedulingPolicy']}:{unit['Service']['CPUSchedulingPriority']}"
        else:
            result += f" -I {unit['Service']['CPUSchedulingPolicy']}"

    if result:
        return 'start_stop_daemon_args="' + result.strip() + '"\n'
    else:
        return ''

def generate_forking(unit):
    cmd = unit['Service']['ExecStart']
    pidfile = unit['Service']['PIDFile']
    executable = cmd.split()[0]
    args = ' '.join(cmd.split()[1:])
    return f'''
command="{executable}"
command_args="{args}"
pidfile="{pidfile}"
'''

def generate_simple(unit):
    cmd = unit['Service']['ExecStart']
    executable = cmd.split()[0]
    args = ' '.join(cmd.split()[1:]) if len(cmd.split()) > 1 else ""
    return f'''
supervisor="supervise-daemon"
command="{executable}"
command_args="{args}"
'''

def generate_oneshot(unit):
    cmd = unit['Service']['ExecStart']
    executable = cmd.split()[0]
    args = ' '.join(cmd.split()[1:])
    return f'''
command="{executable}"
command_args="{args}"
'''

def generate_user(unit):
    if 'User' in unit['Service']:
        if 'Group' in unit['Service']:
            return f'command_user="{unit["Service"]["User"]}:{unit["Service"]["Group"]}"\n'
        else:
            return f'command_user="{unit["Service"]["User"]}"\n'
    return ""

def generate_stop(unit):
    if 'ExecStop' not in unit['Service']:
        return ""

    return f'''
stop() {{
\tebegin "Stopping $RC_SVCNAME"
\t{unit["Service"]["ExecStop"]}
\teend $?
}}
'''

def generate_reload(unit):
    if 'ExecReload' not in unit['Service']:
        return ""

    return f'''
reload() {{
\tebegin "Reloading $RC_SVCNAME"
\t{unit["Service"]["ExecReload"]}
\teend $?
}}
'''

def convert(raw_input):
    parsed = parse_ini_string(raw_input)
    validated = validate(parsed)
    if validated:
        return validated

    result = f'''#!/sbin/openrc-run

name=$RC_SVCNAME
description="{parsed["Unit"]["Description"]}"
'''

    service_type = parsed['Service'].get('Type', 'simple')
    print(f"Generating {service_type} unit")
    if service_type == 'simple' or service_type == 'exec':
        result += generate_simple(parsed)
        result += generate_supervise_args(parsed)
    elif service_type == 'oneshot':
        result += generate_oneshot(parsed)
        result += generate_ssd_args(parsed)
    elif service_type == 'forking':
        result += generate_forking(parsed)
        result += generate_ssd_args(parsed)

    result += generate_user(parsed)
    result += generate_depend(parsed)
    result += generate_stop(parsed)
    result += generate_reload(parsed)

    return result

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert a unit file to an OpenRC script")
    parser.add_argument("input_file", help="Path to the unit file")
    parser.add_argument("output_file", nargs="?", help="Path to the output OpenRC script (default: stdout)")
    args = parser.parse_args()

    try:
        with open(args.input_file, "r") as f:
            raw_input = f.read()
    except FileNotFoundError:
        print(f"Error: {args.input_file} not found.")
        exit(1)

    try:
        result = convert(raw_input)
        if args.output_file:
            with open(args.output_file, "w") as f:
                f.write(result)
        else:
            print(result)
    except Exception as e:
        print(f"Error: {e}")
        exit(1)
