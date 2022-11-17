import pandas as pd
import numpy as np
import requests
import json
import os
import shutil
from bs4 import BeautifulSoup
import io 
import zipfile 

def get_voteview():
    memberurl = 'https://voteview.com/static/data/out/members/HS117_members.csv'
    cvoteurl = 'https://voteview.com/static/data/out/rollcalls/HS117_rollcalls.csv'
    memvoteurl = 'https://voteview.com/static/data/out/votes/HS117_votes.csv'
    members_vv = pd.read_csv(memberurl)
    cvote_vv = pd.read_csv(cvoteurl)
    memvote_vv = pd.read_csv(memvoteurl)
    return members_vv, cvote_vv, memvote_vv

def get_useragent():
    useragent_url = 'https://httpbin.org/user-agent'
    r = requests.get(useragent_url)
    useragent = json.loads(r.text)['user-agent']
    return useragent

def get_propublica(propublica_token, useragent, email):
    headers = {'X-API-Key': propublica_token,
          'User-Agent': useragent,
          'From': email}
    root = 'https://api.propublica.org'
    congress = '117'
    chamber = 'house'
    memberendpoint = '/congress/v1/{congress}/{chamber}/members.json'.format(congress=congress, chamber=chamber)
    r = requests.get(root + memberendpoint, headers = headers)
    myjson = json.loads(r.text)
    house_pp = pd.json_normalize(myjson, record_path = ['results', 'members'])
    chamber = 'senate'
    memberendpoint = '/congress/v1/{congress}/{chamber}/members.json'.format(congress=congress, chamber=chamber)
    r = requests.get(root + memberendpoint, headers = headers)
    myjson = json.loads(r.text)
    senate_pp = pd.json_normalize(myjson, record_path = ['results', 'members'])
    members_pp = pd.concat([house_pp, senate_pp], ignore_index=True)
    return members_pp

def merge_members(members_pp, members_vv):
    # Extract last name from Voteview full name
    members_vv['last_name'] = members_vv['bioname'].str.split(pat=',', expand=True)[0]
    
    #Convert last name to uppercase to facilitate matching
    members_pp['last_name'] = members_pp['last_name'].str.upper()
    members_vv['last_name'] = members_vv['last_name'].str.upper()
    
    #Strip accent characters from the last names
    members_pp['last_name'] = members_pp['last_name'].str.normalize('NFKD').str.encode('ascii', errors='ignore').str.decode('utf-8')
    members_vv['last_name'] = members_vv['last_name'].str.normalize('NFKD').str.encode('ascii', errors='ignore').str.decode('utf-8')
    
    #Extract birth year from ProPublica
    members_pp['born'] = members_pp['date_of_birth'].str.split(pat='-', expand=True)[0]
    
    #Convert birthyears to strings to facilitate matching
    members_vv['born'] = members_vv['born'].astype('str')
    members_pp['born'] = members_pp['born'].astype('str')
    
    #Correct mistaken names and birth years
    members_vv.loc[members_vv['last_name'] == 'LEGER FERNANDEZ', 'last_name'] = 'FERNANDEZ'
    members_pp.loc[members_pp['last_name'] == 'OMAR', 'born'] = '1982'
    members_pp.loc[members_pp['last_name'] == 'PFLUGER', 'born'] = '1978'
    members_vv.loc[members_vv['last_name'] == 'PFLUGER', 'born'] = '1978'
    members_pp.loc[members_pp['last_name'] == 'FULCHER', 'born'] = '1962'
    
    #Merge data (we've already done the steps to confirm the merge works -- don't skip those steps!)
    members_total = pd.merge(members_vv, members_pp,
                        left_on = ['last_name', 'born', 'state_abbrev'],
                        right_on = ['last_name', 'born', 'state'],
                        how = 'right')
    
    #Restrict the columns to only the ones we want to use, and rename key columns
    tokeep = ['title', 'short_title','first_name', 'middle_name', 'last_name', 'suffix',
              'congress', 'chamber', 'icpsr', 'state', 'district', 'at_large',
              'gender', 'party', 'date_of_birth', 'leadership_role',
              'twitter_account', 'facebook_account', 'youtube_account', 
              'url', 'rss_url', 
              'seniority', 'next_election',
              'total_votes', 'missed_votes', 'total_present',
              'office', 'phone', 'fax', 
              'missed_votes_pct', 'votes_with_party_pct', 'votes_against_party_pct', 'nominate_dim1',  
              'id', 'api_uri',
              'last_updated']
    members_total = members_total[tokeep]
    members_total = members_total.rename({'nominate_dim1':'DWNOMINATE',
                                         'id':'propublica_id',
                                         'api_uri':'propublica_endpoint'}, axis=1)
    return members_total
    
def get_bills_pp(propublica_token, useragent, email,
                 congress='117', chamber='both', billtype='introduced', offset=0):
    headers = {'X-API-Key': propublica_token,
              'User-Agent': useragent,
              'From': email}
    root = 'https://api.propublica.org'
    endpoint = f'/congress/v1/{congress}/{chamber}/bills/{billtype}.json'
    params = {'offset': offset}
    r = requests.get(root + endpoint, headers=headers, params=params)
    myjson = json.loads(r.text)
    num_results = myjson['results'][0]['num_results']
    bills = myjson['results'][0]['bills']
    
    return bills, num_results

def download_govinfo(path='/contrans/billsdata', congress = ['117'], session = ['1','2']):
    billtype = ['hconres','hjres','hr','hres','s','sconres','sjres','sres']
    root = 'https://www.govinfo.gov/bulkdata/BILLS/'
    urls = [root]
    urls = [u + c + '/' + s + '/' + b + '/BILLS-' + c + '-' + s + '-' + b + '.zip'
            for u in urls 
            for c in congress 
            for s in session
            for b in billtype]
    for u in urls:   
        r = requests.get(u)
        z = zipfile.ZipFile(io.BytesIO(r.content))
        z.extractall(path)


def get_bill_files(path='/contrans/billsdata', if_exists='ignore'):
    if not os.path.exists(path):
        os.makedirs(path)
        download_govinfo(path)
        return
    if os.path.exists(path) and if_exists=='replace':
        shutil.rmtree(path)
        os.makedirs(path)
        download_govinfo(path)
        return
    if os.path.exists(path) and if_exists=='ignore':
        return
    else:
        return
    
def add_bill_text(bill, path='/contrans/billsdata'):
    slug = bill['bill_slug']
    
    # Find the bill in /billsdata
    try:
        billfile = [f for f in os.listdir(path) if slug in f]
        billfile = billfile[0]
    except:
        return
    
    # Load the file as string
    with open(f"{path}/{billfile}") as f:
        xml_data = f.read()
    
    # Parse the file with lxml and beautifulsoup
    mysoup = BeautifulSoup(xml_data, features="xml")
    
    # Extract text
    bill_text = [m.text for m in mysoup.find_all('text')]
    bill_text = ' '.join(bill_text)
    
    # update json record
    bill.update({'bill_text': bill_text})
    
def build_mongo_db(mongo_username, mongo_password, mongo_init_db, propublica_token, email):
    
    get_bill_files(if_exists='ignore')
    
    useragent = get_useragent()
    
    myclient = pymongo.MongoClient(f"mongodb://{mongo_username}:{mongo_password}@mongo:27017/{mongo_init_db}?authSource=admin")
    
    contrans_db = myclient['contrans']
    
    collist = contrans_db.list_collection_names()
    if "bills" in collist:
      contrans_db.bills.drop()

    bills = contrans_db['bills']
    
    i = 0
    while 1==1:
        bills_list, num_results = getdata.get_bills_pp(propublica_token, useragent, email=email, offset=20*i)
        if num_results == 0:
            print('Done!')
            break
        print(f'Now getting bills {20*i + 1} through {20*(i+1)}')
        for b in bills_list:
            getdata.add_bill_text(b)
        bills_insert = bills.insert_many(bills_list)
        i += 1