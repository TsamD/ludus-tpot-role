#!/usr/bin/env python3
import yaml

config = {
    'ludus': [
        {
            'vm_name': "{{ range_id }}-tpot-server",
            'hostname': "{{ range_id }}-tpot",
            'template': 'ubuntu-24.04-x64-server-template',
            'vlan': 100,
            'ip_last_octet': 10,
            'ram_gb': 8,
            'cpus': 4,
            'linux': True,
            'testing': {
                'snapshot': False,
                'block_internet': False
            },
            'roles': [
                'yudus.ludus_tpot_server'
            ]
        },
        {
            'vm_name': "{{ range_id }}-hiv-sensor",
            'hostname': "{{ range_id }}-hiv",
            'template': 'ubuntu-24.04-x64-server-template',
            'vlan': 100,
            'ip_last_octet': 11,
            'ram_gb': 4,
            'cpus': 2,
            'linux': True,
            'testing': {
                'snapshot': False,
                'block_internet': False
            },
            'roles': [
                'yudus.ludus_hiv_sensor'
            ]
        }
    ]
}

with open("ludus-range-config.yml", "w") as f:
    yaml.dump(config, f, default_flow_style=False)

print("✔️ Fichier ludus-range-config.yml généré avec succès.")
