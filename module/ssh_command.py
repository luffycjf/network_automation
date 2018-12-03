#!/usr/bin/python
#-*- coding:utf-8 -*-

ANSIBLE_METADATA = {'status': ['preview'],
                    'supported_by': 'community',
                    'metadata_version': '1.0'}

DOCUMENTATION = ''' 
---
module: ssh_command
version_added: "1.0"
short_description: run commands on network devices.
description:
     - run commands on network devices.
options:
  command:
    description:
      - network devices command,if you use configfile , thi can be ''
    required: true
  address:
    description:
      - remote network devices ip address
    required: true
  port:
    description:
      - remote network devices ssh port
    required: false
    default: 22
  username:
    description:
      - remote network devices ssh username
    required: true
  password:
    description:
      - remote network devices ssh user password
    required: true
  configfile:
    description:
      - a config file,if you don't use it,this can be ''
    required: false
  command_interval:
    description:
      - the interval between two commands
    required: False
    default: 0.5
  vendor:
    description:
      - the device's vendor(HUAWEI,CISCO,JUNIPER,GENERAL)
    required: False
    default: GENERAL
  stdjudge:
    description:
      - the output need confirm ,like [Y/N]
    required: False
    default: ''
  stdconfirm:
    description:
      - the confirm command,like Y
    required: False
    default: ''
author:
    - "jeffrycheng"
'''

EXAMPLES = """
---

- hosts: localhost
  gather_facts: no
  vars:
    port: 22
    username: "tencent"
    password: "tencent"
    address: "192.168.157.132"
    command_interval: 0.5
    vendor: GENERAL
    stdjudge: "Y/N"
    stdconfirm: "Y"

  tasks:
    - name: set ntp
      ssh_command:
        port: "{{ port }}"
        address: "{{ address }}"
        username: "{{ username }}"
        password: "{{ password }}"
        command_interval: "{{ command_interval }}"
	vendor: {{ vendor }}
	stdjudge: {{ stdjudge }}
        stdconfirm: {{ stdconfirm }}
        command: ''
        configfile: ntp.txt

    - name: display version
      ssh_command:
	port: 22
	address: 192.168.1.1
	username: test
	password: test123
	command_interval: 0.1
	vendor: HUAWEI
	stdjudge: "Y/N"
	stdconfirm: "Y"
	command: 'display version\nsave'
	configfile: ''
"""

RETUN = """
stdout:
  description: the set of responses from the commands
  returned: always
  type: list
  sample: ['...', '...']

command:
  description: run command
  returned: always
  type: str
  sample: display version
"""



import time
import re

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_bytes
from ansible.errors import AnsibleError, AnsibleConnectionFailure


stdmore = re.compile(r"-[\S\s]*[Mm]ore[\S\s]*-")

general_endcondition = re.compile(r"\S+[#>\]]\s*[\n\r]")
hw_endcondition = re.compile(r"\S+[>\]]\s*[\n\r]")
cisco_endcondition = re.compile(r"\S+#\s*[\n\r]")
juniper_endcondition = re.compile(r"\S+[#\]]\s*[\n\r]")


try:
  import paramiko
except ImportError:
  raise AnsibleError("paramiko is not installed, please use pip install paramiko")


class ssh_comm(object):
    def __init__(self,address,username,password,port=22):
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.client.connect(address, port=port, username=username, password=password, look_for_keys=False,allow_agent=False)
        self.shell = self.client.invoke_shell()
        while True:
            time.sleep(0.5)
            if self.shell.recv_ready() or self.shell.recv_stderr_ready():
                break
        self.shell.recv('')
    def recv_all(self,interval,condition_type,stdjudge,stdconfirm):
	if condition_type == 'HUAWEI':
	    condition = hw_endcondition
	elif condition_type == 'CISCO':
	    condition = cisco_endcondition
	elif condition_type == 'JUNIPER':
	    condition = juniper_endcondition
	else:
	    condition = general_endcondition
	while True:
	    time.sleep(interval)
	    if self.shell.recv_ready() or self.shell.recv_stderr_ready():
		break
	output = self.shell.recv(4096)
	if (stdjudge != '') and (stdjudge in output):
	    self.shell.send(stdconfirm+'\n')
	self.shell.send('\n')
	while True:
	    if stdmore.findall(output):
		break
	    elif condition.findall(output):
		output = '\r\n'.join(output.split('\n')[1:-2])
		break
	    while True:
		time.sleep(interval)
		if self.shell.recv_ready() or self.shell.recv_stderr_ready():
		    break
	    output += self.shell.recv(4096)
	return output
    def send_command(self,command_interval,command,endcondition,stdjudge,stdconfirm):
        command += "\n"
        self.shell.send(command)
        stdout = self.recv_all(interval=command_interval,condition_type=endcondition,stdjudge=stdjudge,stdconfirm=stdconfirm)
        data = stdout.split('\n')
        while stdmore.findall(data[-1]):
            self.shell.send(" ")
            while True:
                time.sleep(command_interval)
                if self.shell.recv_ready() or self.shell.recv_stderr_ready():
                    break
            tmp = self.recv_all(interval=command_interval,condition_type=endcondition,stdjudge=stdjudge,stdconfirm=stdconfirm)
            data = tmp.split('\n')
            stdout += tmp
        return stdout
    def close(self):
	if self.client is not None:
	    self.client.close()
    def run(self,cmds,command_interval,endcondition,stdjudge,stdconfirm):
	stderr = ['^','ERROR','Error','error','invalid','Invalid','Ambiguous','ambiguous']
        stdout = ''
        rc = 0
        for cmd in cmds.split('\n'):
            stdout += self.send_command(command=cmd,command_interval=command_interval,endcondition=endcondition,stdjudge=stdjudge,stdconfirm=stdconfirm)
        for err in stderr:
            if err in stdout:
		rc = 1
        return rc, stdout
            
            
def main():
    module = AnsibleModule(
    argument_spec = dict(
    configfile=dict(required=False,type='str'),
    command=dict(required=True, type='str'),
    address=dict(required=True, type='str'),
    port=dict(required=False, type='int', default=22),
    username=dict(required=True, type='str'),
    password=dict(required=True, type='str', no_log=True),
    command_interval=dict(required=False, type='float',default=0.5),
    vendor=dict(required=False, type='str',default='general'),
    stdjudge=dict(required=False, type='str',default=''),
    stdconfirm=dict(required=False, type='str',default='')),
    supports_check_mode=True)
    command = to_bytes(module.params['command'], errors='surrogate_or_strict')
    configfile = to_bytes(module.params['configfile'], errors='surrogate_or_strict')
    address = to_bytes(module.params['address'], errors='surrogate_or_strict')
    username = to_bytes(module.params['username'], errors='surrogate_or_strict')
    password = to_bytes(module.params['password'], errors='surrogate_or_strict')
    command_interval = to_bytes(module.params['command_interval'], errors='surrogate_or_strict')
    vendor = to_bytes(module.params['vendor'], errors='surrogate_or_strict')
    stdjudge = to_bytes(module.params['stdjudge'], errors='surrogate_or_strict')
    stdconfirm = to_bytes(module.params['stdconfirm'], errors='surrogate_or_strict')
    result = {'changed': False}
    if configfile != '':
        try:
            with open(configfile) as f:
                command = f.read()
            command = to_bytes(command, errors='surrogate_or_strict')
        except Exception as e:
            raise AnsibleError('Config file is wrong\n' + str(e) )
    try:
        connection = ssh_comm(address=address, username=username, password=password, port=module.params['port'])
    except Exception as e:
        raise AnsibleConnectionFailure(str(e))
    try:
        rc,stdout = connection.run(cmds=command,command_interval=float(command_interval),endcondition=vendor.upper(),stdjudge=stdjudge,stdconfirm=stdconfirm)
    except Exception as e:
        raise AnsibleError('Exec command error.\n' + str(e))

    if rc == 0:
        result['changed'] = True
    elif rc == 1:
        module.fail_json(msg=stdout)
    connection.close()
    result.update({'command': command,'rc': rc,'stdout': stdout})
    module.exit_json(**result)

if __name__ == '__main__':  
    main() 
