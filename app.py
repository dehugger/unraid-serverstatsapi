#standard library
import os, sys, psutil, time, json, re
#other
import arrow #time
from flask import Flask, request
from flask_restful import Resource, Api

'''
set docker environment variables for $HOSTNAME
psutils for cpu, memory, disks, network
'''

class Config:
    #replace these with docker variables
    docker_location = '/emhttp/plugins/dynamix.docker.manager/docker.json'
    smart_location = '/emhttp/smart/'
    ini_location = '/emhttp/'
    ini_files = [
    'cpuload.ini',
    'devs.ini',
    'diskload.ini',
    'disks.ini',
    'monitor.ini',
    'network.ini',
    'shares.ini',
    'users.ini',
    'var.ini'
    ]

def basic_ini_parse(in_ini):
    if in_ini != '':
        d = {}
        lines = in_ini.split('\n')
        root_key = None
        for l in lines:
            if l != '':
                if l[0] == '[':
                    root_key = l.replace('[','').replace(']','')
                    root_key = root_key.replace('"','')
                    if root_key in d.keys():
                        pass
                    else:
                        d[root_key] = {}
                else:
                    key, value = l.split('=')
                    key = key.replace('"','')
                    value = value.replace('"','')
                    if root_key:
                        d[root_key][key] = value
                    else:
                        d[key] = value
        return d

def smart_file_parser(sf_raw):
    try:
        disk = re.match(r'!!(.*)!!',sf_raw).group(1)
        try:
            table = re.findall(r'(ID#.*)',sf_raw,flags=re.DOTALL)[0]
        except IndexError:
            table = None
        if table == None:
            table = 'No Table Data'
        return (disk,table)
    except Exception as e:
        raise e

class DataCompiler(object):
    def __init__(self):
        self.system_vars = self.get_system_vars()
        self.data = {
            'timestamp':str(arrow.now()),
            'cpu':self.get_cpu_stats(),
            'mem':self.get_mem_stats(),
            'temp':self.get_temp_stats(),
            'network':self.get_network_stats(),
            'docker':self.get_docker_stats(),
            'ini':self.get_ini_stats(),
            'smart':self.get_smart_stats()
        }

    def refresh(self):
        self.data = {
            'timestamp':arrow.now(),
            'cpu':self.get_cpu_stats(),
            'mem':self.get_mem_stats(),
            'temp':self.get_temp_stats(),
            'network':self.get_network_stats(),
            'docker':self.get_docker_stats(),
            'ini':self.get_ini_stats(),
            'smart':self.get_smart_stats()
        }

    def get_system_vars(self):
        return {
            'hostname':os.getenv('HOSTNAME')
        }

    def get_cpu_stats(self):
        return {
            'epoc':time.time(),
            'core_util':psutil.cpu_percent(interval=1, percpu=True),
            'core_count':psutil.cpu_count(logical=False),
            'thread_count':psutil.cpu_count()
        }

    def get_mem_stats(self):
        return {
            'epoc':time.time(),
            'virtual':psutil.virtual_memory(),
            'swap':psutil.swap_memory()
        }

    def get_temp_stats(self):
        return {
            'epoc':time.time(),
            'temps':psutil.sensors_temperatures(),
            'fans':psutil.sensors_fans()
        }

    def get_network_stats(self):
        #this probably wont return anything usefull in docker
        return {
            'epoc':time.time(),
            'addrs':psutil.net_if_addrs(),
            'stats':psutil.net_if_stats(),
            'counters':psutil.net_io_counters(pernic=True)
        }

    def get_ini_stats(self):
        ini = {}
        try:
            for i in Config.ini_files:
                with open(Config.ini_location + i, 'r') as f:
                    ini[i] = basic_ini_parse(f.read())
        except Exception as e:
            ini['exception'] = str(e)
        return ini

    def get_docker_stats(self):
        try:
            with open(Config.docker_location, 'r') as f:
                return json.loads(f.read())
        except:
            return None

    def get_smart_stats(self):
        smart = {}
        try:
            for i in os.listdir(Config.smart_location):
                f_path = os.path.join(Config.smart_location, i)
                if os.path.isfile(f_path):
                    with open(f_path, 'r') as f:
                        disk,table = smart_file_parser(f.read())
                    if disk != None and table != None:
                        smart[disk] = table
        except Exception as e:
            smart['exception'] = str(e)
        return smart


app = Flask(__name__)
api = Api(app)
data = DataCompiler()

class SystemStats(Resource):
    def get(self, statblock='all'):
        return {'data':data.data}

class DockerStats(Resource):
    def get(self):
        return {'docker':data.get_docker_stats()}

class DiskStats(Resource):
    def get(self):
        return {'disks':data.data['ini']['disks.ini']}

class NetStats(Resource):
    def get(self):
        return {'network':data.data['ini']['network.ini']}

class SharesStats(Resource):
    def get(self):
        return {'shares':data.data['ini']['shares.ini']}

class CPUStats(Resource):
    def get(self):
        return {'cpu':data.get_cpu_stats()}

class MemStats(Resource):
    def get(self):
        return {'mem':data.get_mem_stats()}

class TempStats(Resource):
    def get(self):
        return {'temp':data.get_temp_stats()}

class SmartStats(Resource):
    def get(self):
        return {'smart':data.get_smart_stats()}

api.add_resource(SystemStats, '/')
api.add_resource(DockerStats, '/docker')
api.add_resource(DiskStats, '/disks')
api.add_resource(NetStats, '/network')
api.add_resource(SharesStats, '/shares')
api.add_resource(CPUStats, '/cpu')
api.add_resource(MemStats, '/memory')
api.add_resource(TempStats, '/temp')
api.add_resource(SmartStats, '/smart')

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)