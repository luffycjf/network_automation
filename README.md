# network_automation
An ansible-based, multi-vendor network device configuration automatically generates and delivery system

**下载文件**<br/>

```javascript
git clone https://github.com/luffycjf/network_automation
```
**安装ansible和模块**<br/>

```javascript
yum -y install ansible<br/>
sed -i "s/#library/library/g" /etc/ansible/ansible.cfg<br/>
mkdir -p /usr/share/my_modules/<br/>
cd network_automation<br/>
cp module/ssh_command.py /usr/share/my_modules/ <br/>
```
如果已经安装了ansible，直接把module文件夹下的ssh_command.py放到ansible配置的模块目录下即可。<br/>

**使用**<br/>
目录下主文件network_automation.yml就是一个playbook，其中的含义[博客](https://jeffrycheng.com)上面都有说，两个task分别是生成配置文件和下发配置用的，写了一些配置模版和变量分别放在templates和vars文件夹中，目前时间和精力原因只更新了部分基础配置，不涉及interface和路由部分，后续会补充完整，有兴趣的也可以自己来写更多的。<br/>

调用ansible-playbook network_automation.yml即可使用<br/>

```javascript
---
- name: gengerate configuration
  hosts: localhost
  vars:
    model: h3c_v7
    module: general
    port: 22
    username: "test"
    password: "test"
    command_interval: 0.5
    stdjudge: "Y/N"
    stdconfirm: "Y"

  vars_files:
    - "vars/{{ model }}/{{ module }}.yml"

  tasks:
    - name: generate configuration
      template:
        src: "templates/{{ model }}/{{ module }}.j2"
        dest: "config/{{ item.hostname }}.txt"
      with_items:
        - { hostname: 'h3c-test1'}

    - name: config device
      ssh_command:
        port: "{{ port }}"
        username: "{{ username }}"
        password: "{{ password }}"
        address: "{{ item.mgtip }}"
        command_interval: "{{ command_interval }}"
        stdjudge: "{{ stdjudge }}"
        stdconfirm: "{{ stdconfirm }}"
        command: ''
        configfile: "config/{{ item.hostname }}.txt"
      with_items:
        - { hostname: 'h3c-test1', mgtip: '1.1.1.1' }
```


基于这套系统的网络架构规划，自动化网络变更等场景，我将会在后续文章中介绍。
