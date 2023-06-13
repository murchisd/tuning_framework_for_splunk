
import getpass, sys, time, os
import requests
from pathlib import Path
import argparse
import tarfile
import collections
import stat
import re
import shutil
import tarfile
import tempfile
import zipfile
import json
# Splunk Libraries
import configuration_file
import configuration_parser

def build_app(path,tgz_file):
    with tarfile.open(tgz_file, "w:gz") as tar:
        tar.add(path, arcname=path.name)

def make_tree(parent,indent,return_array,prefix,pwd):
    return_array.append(prefix+str(parent))
    pwd=pwd / parent 
    if pwd.is_file():
        return
    children=pwd.iterdir()
    for child in children:
        make_tree(child.name,indent+"`` ",return_array,indent +"|--- ",pwd)

def parse_config(file_path):
    if file_path.exists():
        config_file=configuration_file.ConfigurationFile()
        with file_path.open() as file:
            config_file = configuration_parser.parse(
            file, config_file, configuration_parser.configuration_lexer)
        return config_file

def update_app_settings(config_file,app_settings):
    app_sections = config_file.section_names()
    for section in app_sections:
        items = config_file.items(section)
        #items array of items with key, value, line number
        for item in items:
            app_settings[item[0]]=item[1]
    return app_settings

def gen_docs(app_path):
    if (app_path.is_file()):
        print("Path must point to directory not a file")
        sys.exit()
    if app_path.is_dir():
        # Load default app.conf settings
        # app.conf spec here https://docs.splunk.com/Documentation/Splunk/8.2.2/Admin/Appconf
        app_settings={}
        default_dir = app_path / "default"
        default_app_path =  default_dir / "app.conf"
        config_file = parse_config(default_app_path)
        if config_file:
            app_settings = update_app_settings(config_file,app_settings)
        
        # Load local app.conf settings
        # Takes precedence over default in Splunk so app_settings will show what Splunk would apply
        local_dir = app_path / "local"
        default_app_path = local_dir / "app.conf"
        config_file = parse_config(default_app_path)
        if config_file:
            app_settings = update_app_settings(config_file,app_settings)
        
        #Get Sections of all confs in default and local
        '''confs=collections.defaultdict(list)
        if default_dir.exists():
            for conf in default_dir.iterdir():
                if conf.is_file():
                    conf_file = parse_config(conf)
                    for section in conf_file.section_names():
                        if section not in confs[conf.name]:
                            confs[conf.name].append(section)
        
        if local_dir.exists():
            for conf in local_dir.iterdir():
                if conf.is_file():
                    conf_file = parse_config(conf)
                    for section in conf_file.section_names():
                        if section not in confs[conf.name]:
                            confs[conf.name].append(section)'''
        
        #Get all Confs and display full fule in preview
        confs=collections.defaultdict(list)
        if local_dir.exists():
            for conf in local_dir.iterdir():
                if conf.is_file():
                    if conf.name != "app.conf":
                        confs[conf.name].append(conf)
                    
        if default_dir.exists():
            for conf in default_dir.iterdir():
                if conf.is_file():
                    if conf.name != "app.conf":
                        confs[conf.name].append(conf)
                              
        #Build directory tree structure string
        basename=app_path.name
        parent_path = Path(app_path.parent)
        dir_array=[]
        make_tree(basename,"",dir_array,"",parent_path) 
        
        
        #Format the README file
        readme = app_path / "README.md"
        with readme.open(mode='w') as file:
            #Write label as Header
            #print(app_settings)
            if "label" in app_settings:
                file.write("# {}\n".format(app_settings['label']))
            else:
                file.write("# {}\n".format(app_path.name))
            file.write("\n## App Properties \n")
            for setting in sorted(app_settings.items()):
                file.write("{}: {}  \n".format(setting[0],setting[1]))
            file.write("\n## App Structure \n```\n")
            file.write("\n".join(dir_array))
            file.write("\n```\n## App Confs \n")
            for conf_type in confs:
                file.write("### {} \n".format(conf_type))
                for conf in confs[conf_type]:
                    if "local" in str(conf.parent):
                        file.write("#### Local \n")
                    else:
                        file.write("#### Default \n")
                    file.write("```\n")
                    file.write(conf.read_text())
                    file.write("\n```\n")
                #for section in confs[conf]:
                #    file.write("* {} \n".format(section))



def main(args):

    authentication_host='api.splunk.com'
    acs_api_host='admin.splunk.com'
    appinspect_api_host="appinspect.splunk.com"
    
    user=input("User: ")
    pwd=getpass.getpass("Password: ")
    
    if args.install:
        if args.stack is None:
            parser.error("--install requires stack name (-s or --stack)")
        acs_token=getpass.getpass("ACS Token: ")
        stack=args.stack

    proxies={}
    if args.proxy:
        proxies['https']=args.proxy
   
    #url="https://{0}/{1}/adminconfig/v2/status".format(acs_api_host,stack)
    url="https://{0}/2.0/rest/login/splunk".format(authentication_host)
    print("Authenticating to splunk web...")
    r = requests.get(url,proxies=proxies,auth=(user,pwd))

    if(r.status_code==200):
        print("Authentication successful...")
    else:
        print("Authentication Failed, exiting...")
        sys.exit()
    
    app_path=Path(args.file)
    
    print("Generating documentation...")
    gen_docs(app_path)
    print("Documentation complete...")
    
    if app_path.is_dir():
        build_path=app_path.resolve().parent
        tgz_file=build_path / app_path.name
        tgz_file=tgz_file.with_suffix('.tgz')
        print("Building app...")
        build_app(app_path,tgz_file)
        print("Build complete...")
    else:
        print("Path must point to directory not a file")
        sys.exit()

    print("Validating app...")
    url="https://{0}/v1/app/validate".format(appinspect_api_host)
    appinspect_token=r.json()['data']['token']
    r = requests.post(url,proxies=proxies,headers={'Authorization': 'Bearer {}'.format(appinspect_token)},data={'included_tags':'private_app'},files={'app_package': tgz_file.open('rb')})
    
    status_link='https://{0}'.format(appinspect_api_host)
    report_link='https://{0}'.format(appinspect_api_host)
    for link in r.json()['links']:
        try:
            if link['rel']=='status':
                status_link='https://{0}{1}'.format(appinspect_api_host,link['href'])
            elif link['rel']=='report':
                report_link='https://{0}{1}'.format(appinspect_api_host,link['href'])
        except Exception as e:
            print(e)
                
    r = requests.get(status_link,proxies=proxies,headers={'Authorization': 'Bearer {}'.format(appinspect_token)})
    status=r.json()['status']
    while status=="PROCESSING":
        time.sleep(3)
        r = requests.get(status_link,proxies=proxies,headers={'Authorization': 'Bearer {}'.format(appinspect_token)})
        status=r.json()['status']
    print("Validation complete...")
    r = requests.get(report_link,proxies=proxies,headers={'Authorization': 'Bearer {}'.format(appinspect_token)})
    print("Writing Report...")
    report_path=app_path.resolve().parent
    report_file=build_path / (app_path.name + '_validation.log')
    with report_file.open(mode='w') as file:
        json.dump(r.json(),file,indent=4)
    print("Report complete...")
    print("\nReport Summary")
    print(r.json()['summary'])
    
    if args.install:
        if r.json()['summary']['error']!=0 or r.json()['summary']['failure']!=0:
            print("App did not pass validation. Please address issues and retry.")
            sys.exit()
        if r.json()['summary']['manual_check']!=0:
            print("App may require Splunk manual review. Please review app and submit ticket to Splunk Support if necessary.")
            sys.exit()
        print("Installing App...")
        url="https://{0}/{1}/adminconfig/v2/apps/victoria".format(acs_api_host,stack)
        r = requests.post(url,proxies=proxies,headers={'X-Splunk-Authorization': '{}'.format(appinspect_token),'Authorization':'Bearer {}'.format(acs_token),'ACS-Legal-Ack':'Y'},data=tgz_file.open('rb'))
        print(r.json())
        
def create_parser():
    parser = argparse.ArgumentParser(description='Perform app validation and install functions through ACS API')
    parser.add_argument("-f","--file",type=str, required=True, help="Path to Splunk app directory")
    parser.add_argument("--proxy",type=str, help="URL for https proxy")
    parser.add_argument("-s","--stack",type=str, help="Name of Splunk Stack for ACS API install - only required if install flag set")
    parser.add_argument("-i","--install",default=False,action='store_true',required=False, help="Argument to indicate whether app should be installed after validation")
    return parser
    

if __name__ == "__main__":
    parser = create_parser()
    args = parser.parse_args()
    main(args)