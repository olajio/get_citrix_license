"""
The script is remotely connecting to a machine from where we can check the Citrix Licenses we have available.
AMDB: 12004
"""
import os
import re
from datetime import datetime
from argparse import ArgumentParser
import json
import winrm

# from pathlib import Path
#
# import json_log_format as jlf
#
# jlf.service_name = Path(__file__).stem
# jlf.service_type = 'logstash_monitoring'
# jlf.json_logging.init_non_web(custom_formatter=jlf.CustomJSONLog, enable_json=True)
# logger = jlf.logging.getLogger(__name__)
# logger.setLevel(jlf.logging.DEBUG)
# logger.addHandler(jlf.logging.StreamHandler(jlf.sys.stdout))


def extract_licenses(license_result):
    res = re.findall(r'\d+', license_result)
    return res


def main():
    username = 'service-elasticauto'

    parser = ArgumentParser(description='Citrix license count check')
    parser.add_argument('--password', required=True)
    parser.add_argument('--hostname', required=True)
    parser.add_argument('--domain', required=True)
    args = parser.parse_args()

    password = args.password
    hostname = args.hostname
    domain = args.domain

    cmd_citrix_licenses = """
    $citrix_licenses = (Invoke-command -scriptblock { cmd.exe /c ' C:\\Progra~2\\Citrix\\Licensing\\LS\\lmstat.exe /c @localhost /a |find "XDT_PLT_CCS" ' })
    $citrix_licenses
    """

    try:
        session = winrm.Session(f"{hostname}.{domain}", auth=(username, password), transport='ntlm')
    except Exception as e:
        # print(f"There was a problem establishing the session. {e}")
        return

    citrix_licenses = session.run_ps(cmd_citrix_licenses)
    # print('Citrix licenses output: \n', citrix_licenses.std_out.decode('utf-8').split(':'))
    # print('Citrix licenses errors: ', citrix_licenses.std_err.decode('utf-8'))
    response = citrix_licenses.std_out.decode('utf-8').split(':')
    # print(f"response: {response}")
    licenses = extract_licenses(response[1].split(')')[0])
    cert_expiration = response[-1].replace('\r', '').replace('\n', '')
    # cert_expiration = cert_expiration(expiry_date_str, "%d-%b-%Y").date()
    # expiry_date = datetime.strptime(expiry_date_str, "%d-%b-%Y").date()
    print(f"cert_expiration: {cert_expiration}")
    today = datetime.today().date()
    print(f"today: {today}")
    # days_until_expiry = (cert_expiration - today).days
    # print(f"days_until_expiry: {days_until_expiry}")



    total_licenses = int(licenses[0])
    used_licenses = int(licenses[1])
    free_licenses = total_licenses - used_licenses
    current_time = datetime.now().isoformat()
    service_name = 'citrix_licenses'
    labels_fields = {
        'total_licenses': total_licenses,
        'used_licenses': used_licenses,
        'free_licenses': free_licenses
    }
    service = {
        'name': service_name,
        'type': 'citrix'
    }

    if free_licenses >= 30:
        log_event = {
            '@timestamp': current_time,
            'message': 'Available licenses are over 30!',
            'service': service,
            'log': {
                'level': 'INFO'
            },
            'labels': labels_fields,
            'hostname': hostname,
            'domain': domain
        }
    else:
        log_event = {
            '@timestamp': current_time,
            'message': 'Available licenses are less than 30!',
            'service': service,
            'log': {
                'level': 'ERROR'
            },
            'labels': labels_fields,
            'hostname': hostname,
            'domain': domain
        }

    json_log = json.dumps(log_event)
    print(json_log)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"There was an error executing logstash script - citrix_license_count.py. Error - {str(e)}")
