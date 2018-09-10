import boto3
import subprocess
import os
import json
import requests

github_oauth_token = "0f7e733b4b4fbbd84f3c256b79cf57120de721b7"

github_create_url = "https://api.github.com/orgs/TGFX/repos?access_token=" + github_oauth_token

project_base = "/home/ec2-user/environment"

def confirm(prompt):
    """
    Ask user to enter Y or N (case-insensitive).
    :return: True if the answer is Y.
    :rtype: bool
    """
    answer = ""
    while answer not in ["y", "n"]:
        answer = input(prompt + " [Y/N]? ").lower()
    return answer == "y"

def create (args, env):
    
    if (os.path.isdir(os.path.join(project_base, args.name))):
        print("Error project already exists!")
        return(1)
    
    if (args.project_type == "s3"):
        s3 = boto3.resource('s3')
        client = boto3.client('s3')
        for bucket in s3.buckets.all():
            if (bucket.name == args.domain):
                print("Error: Bucket already exists!")
                return(1)
        
        if (args.domain[0:4] == "www."):
            primary_domain = args.domain[4:]
            secondary_domain = args.domain
        else:
            primary_domain = args.domain
            secondary_domain = "www." + args.domain
            
        log_domain = "logs." + primary_domain
        
        policy_string = """{{
    "Version": "2012-10-17", 
    "Statement": [ {{ 
        "Sid": "PublicReadGetObject", 
        "Effect": "Allow", 
        "Principal": "*",
        "Action": "s3:GetObject", 
        "Resource": "arn:aws:s3:::{0}/*"
    }} ]
}}"""
        
        policy_string = policy_string.format(primary_domain)
        
        bucket_conf = {"LocationConstraint": args.region}
        
        print("This github repository will be created: github.com/TGFX/" + args.name)
        
        print("\nThese aws s3 buckets will be created:")
        print("\nPrimary Bucket: " + primary_domain)
        print("\tRegion: " + args.region)
        print("\tLogging: " + str(not args.logging))
        print("\tHosting: True")
        print("\tPolicy: \n" + policy_string)
        
        print("\nSecondary Bucket: " + secondary_domain)
        print("\tRegion: " + args.region)
        print("\tLogging: False")
        print("\tRedirect: " + primary_domain)
        
        if (not args.logging):
            print("\nLog Bucket: " + log_domain)
            print("\tRegion: " + args.region)
        
        print()
        
        res = confirm("Are you sure you want to confirm these actions?")
        
        if (res == False):
            return(1)
            
        project_file_data = {
            "name": args.name,
            "primary_domain": primary_domain,
            "secondary_domain": secondary_domain,
            "log_domain": log_domain,
            "type": args.project_type,
            "logging": str(not args.logging),
            "region": args.region
        }
        
        #Create github repo
        print ("Creating online github repo... ", end='', flush=True)
        r = requests.post(github_create_url, json={'name': args.name, 'description': 'Description', 'homepage': 'https://github.com', 'private': False})
        if (r.status_code != 201):
            print("Error creating github repository!")
            return(1)
        print("Done")

        #Create local repo
        cwd = os.getcwd()
        project_file_data_str = json.dumps(project_file_data)
        
        print ("Creating local git repo... ")
        
        subprocess.call(['mkdir', os.path.join(project_base, args.name)])
        os.chdir(os.path.join(project_base, args.name))
        with open(os.devnull, 'w') as dev_null:
            subprocess.call(['git', 'init'], stdout=dev_null, stderr=subprocess.STDOUT)
            subprocess.call(['touch', 'README.md'], stdout=dev_null, stderr=subprocess.STDOUT)
            subprocess.call(['git', 'add', 'README.md'], stdout=dev_null, stderr=subprocess.STDOUT)
            
            with open(os.path.join(project_base, args.name, ".tgfx"), "w") as tgfx_file:
                tgfx_file.write(project_file_data_str)
        
            subprocess.call(['git', 'add', '.tgfx'], stdout=dev_null, stderr=subprocess.STDOUT)
            subprocess.call(['git', 'commit', '-m', '"Init commit"'], stdout=dev_null, stderr=subprocess.STDOUT)
            print("Please enter github password: ", end='', flush=True)
            subprocess.call(['curl', '-u', 'OwenTGFX', 'https://api.github.com/user/repos', '-d', '{"name":"' + args.name + '"}', '&>', '/dev/null'], stdout=dev_null, stderr=subprocess.STDOUT)
            subprocess.call(['git', 'remote', 'add', 'origin', 'git@github.com:OwenTGFX/' + args.name + '.git'], stdout=dev_null, stderr=subprocess.STDOUT)
            subprocess.call(['git', 'push', '-u', 'origin', 'master'], stdout=dev_null, stderr=subprocess.STDOUT)
        os.chdir(cwd)
        print("Done")
            
        #Create logging
        if (not args.logging):
            print ("Creating log bucket... ", end='', flush=True)
            response = s3.create_bucket(Bucket=log_domain, CreateBucketConfiguration=bucket_conf, ACL="log-delivery-write")
            print("Created bucket: " + response.name)
        
        #Create primary
        print ("Creating primary bucket... ", end='', flush=True)
        response = s3.create_bucket(Bucket=primary_domain, CreateBucketConfiguration=bucket_conf)
        print("Created bucket: " + response.name)
        
        #Create secondary
        print ("Creating secondary bucket... ", end='', flush=True)
        response = s3.create_bucket(Bucket=secondary_domain, CreateBucketConfiguration=bucket_conf)
        print("Created bucket: " + response.name)
        
        #Primary logging
        print("Configuring primary logging... ", end='', flush=True)
        response = client.put_bucket_logging(
            Bucket=primary_domain,
            BucketLoggingStatus={
                'LoggingEnabled': {
                    'TargetBucket': log_domain,
                    'TargetPrefix': 'root/'
                }
            },
        )
        print("Done")
        
        #Primary hosting
        print("Configuring primary hosting... ", end='', flush=True)
        response = client.put_bucket_website(
            Bucket=primary_domain,
            WebsiteConfiguration={
                'IndexDocument': {
                    'Suffix': 'index.html'
                }
            }
        )
        print("Done")
        
        #Primary policy
        print("Configuring primary policy... ", end='', flush=True)
        response = client.put_bucket_policy(
            Bucket=primary_domain,
            Policy=policy_string
        )
        print("Done")
        
        #Secondary hosting
        print("Configuring secondary hosting... ", end='', flush=True)
        response = client.put_bucket_website(
            Bucket=secondary_domain,
            WebsiteConfiguration={
                'RedirectAllRequestsTo': {
                    'HostName': primary_domain
                }
            }
        )
        print("Done")