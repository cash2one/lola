
# coding: utf-8

# In[29]:

import json
import time
import random
import pymongo
import copy
import MyCommon
from pymongo import MongoClient
from collections import deque
import cassiopeia
from cassiopeia import riotapi
import numpy as np
from sklearn import preprocessing, cluster, decomposition
from scipy.cluster.vq import kmeans,vq
from mpl_toolkits.mplot3d import Axes3D
from sklearn.cluster import KMeans, AffinityPropagation
from sklearn.decomposition import FastICA, PCA
from sklearn import metrics

riotapi.set_region("OCE")
riotapi.set_api_key("79428a9e-5d98-469b-9b9b-429c1a750d24")
riotapi.set_rate_limits((10, 10), (500, 600))
riotapi.print_calls(True)

client = MongoClient()
loladb = client.loladb_zzportal
matches_collection = loladb.matches
print matches_collection.count()
#my last game id: 159185084


# In[13]:

def IsSoloRank(match_type):
    if match_type == 'TEAM_BUILDER_RANKED_SOLO' or match_type == 'TEAM_BUILDER_DRAFT_RANKED_5x5':
        return True
    else:
        return False
    
def GetWinningSide(a_match):
    winning_side = -1
    if a_match['teams'][0]['winner'] == True and a_match['teams'][1]['winner'] == False:
        winning_side = 0
    if a_match['teams'][0]['winner'] == False and a_match['teams'][1]['winner'] == True:
        winning_side = 1 
    return winning_side


# In[31]:

starting_id = 159214821

for i in range(10000):
    try:
        a_match = riotapi.get_match(starting_id + i)
    except:
        print "ERROR. CONTINUE!"
        continue
    a_match = json.loads(a_match.to_json())
    matchVersion = a_match['matchVersion']
    #print a_match['queueType']
    matchMap = a_match['mapId']
    matchDuration = a_match['matchDuration']/60
    matchWinningSide = GetWinningSide(a_match)
    #print a_match['participantIdentities'][0]['player']['summonerName']
    #print a_match['participants'][0]['highestAchievedSeasonTier']
    if matchVersion.startswith('6.24') == False:
        continue
    
    if matchDuration < 20:
        continue
        
    if matchWinningSide == -1:
        continue
        
    if matchMap != 11:
        continue
        
    if matches_collection.find_one({'matchId':a_match['matchId']}) == None:    
        matches_collection.insert_one(a_match)
        print 'SAVED.'


# In[ ]:



