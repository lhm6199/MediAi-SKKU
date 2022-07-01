import requests
import boto3
import json
from typing import Optional
from fastapi import FastAPI

app = FastAPI()

def drug_time(api_url):
    url = api_url

    response = requests.get(url).json()
    detail_description = ""
    brief_description = ""
    drug_list = response['FullStudiesResponse']['FullStudies'][0]['Study']['ProtocolSection']['ArmsInterventionsModule']['InterventionList']['Intervention']
    arm_name = response['FullStudiesResponse']['FullStudies'][0]['Study']['ProtocolSection']['ArmsInterventionsModule']['ArmGroupList']['ArmGroup']

    try:
        detail_description = response['FullStudiesResponse']['FullStudies'][0]['Study']['ProtocolSection']['DescriptionModule']["BriefSummary"]
    except KeyError:
        pass
    try:
        brief_description = response['FullStudiesResponse']['FullStudies'][0]['Study']['ProtocolSection']['DescriptionModule']["DetailedDescription"]
    except KeyError:
        pass

    drug = []
    time_label = ['day','days','week','weeks','month','year']
    time_label2 = ['day','week','month','year']
    amount = ['mg','g ']
    drug_date = []
    left = 0
    right = 0

    drug_dict = {}

    Arm_group = {}
    InterventionDrug = {'ArmGroupList' : []}
    Total_drugName = {'drugs' : {}}


    for arms in arm_name:
        try:
            Arm_group[arms['ArmGroupLabel']] = {'ArmGroupLabel' : '','ArmGroupType' : '', 'ArmGroupDescription' : '', 'InterventionList' : '', 'InterventionDescription' : []}
            Arm_group[arms['ArmGroupLabel']]['ArmGroupLabel'] = arms['ArmGroupLabel']
            Arm_group[arms['ArmGroupLabel']]['ArmGroupType'] = arms['ArmGroupType']
            Arm_group[arms['ArmGroupLabel']]['InterventionList'] = arms['ArmGroupInterventionList']
        except KeyError:
            pass

    #print(Arm_group)

    for i in range(len(drug_list)):
        drug.append(drug_list[i]['InterventionName'])
        drug_dict[drug_list[i]['InterventionName'].lower()] = {'DrugName' : '','Duration' : '', 'Dosage' : ''}

    slpit = detail_description.replace(",", "").split(". ") + brief_description.replace(",", "").split(".")

    for i1 in range(len(slpit)):    
        temp = slpit[i1].split()
        for i2 in range(len(drug)):
            if drug[i2]+ ' ' in slpit[i1]:
                drug_index = temp.index(drug[i2].split()[0])
                for i5 in range(len(time_label)):
                    for i3 in range(drug_index-1, -1, -1):
                        if time_label[i5] == temp[i3]:
                            left = i3
                            break
                    for i4 in range(drug_index, len(temp)):
                        if time_label[i5] == temp[i4]:
                            right = i4
                            break
                if left == 0 and right == 0:
                    continue
                elif left == 0 or abs(drug_index - left) >= abs(drug_index - right):
                    drug_date.append(temp[drug_index : right + 1])
                    drug_dict[temp[drug_index].lower()]['Duration'] = temp[right - 1] + " " + temp[right]


                elif right == 0 or abs(drug_index - left) < abs(drug_index - right):
                    drug_date.append(temp[left-1 :drug_index  + 1])
                    drug_dict[temp[drug_index].lower()]['Duration'] = temp[left - 1] + " " + temp[left]

                left = 0
                right = 0
                
            elif drug[i2].lower() + ' ' in slpit[i1]:
                drug_index = temp.index(drug[i2].split()[0].lower())
                for i5 in range(len(time_label)):
                    for i3 in range(drug_index-1, -1, -1):
                        if time_label[i5] == temp[i3]:
                            left = i3
                            break
                    for i4 in range(drug_index, len(temp)):
                        if time_label[i5] == temp[i4]:
                            right = i4
                            break
                if left == 0 and right == 0:
                    continue
                elif left == 0 or abs(drug_index - left) >= abs(drug_index - right):
                    drug_date.append(temp[drug_index : right + 1])
                    drug_dict[temp[drug_index]]['Duration'] = temp[right - 1] + " " + temp[right]    
                elif right == 0 or abs(drug_index - left) < abs(drug_index - right):
                    drug_date.append(temp[left :drug_index  + 1])
                    drug_dict[temp[drug_index]] = temp[left - 1] + " " + temp[left]
                    drug_dict[temp[drug_index]]['Duration'] = temp[left - 1] + " " + temp[left]
                left = 0
                right = 0
    #print(drug_dict)
    comprehend = boto3.client('comprehend')

    DetectEntitiestext = detail_description
    test = (comprehend.detect_entities(Text=DetectEntitiestext, LanguageCode='en'))


    protocolsection = response['FullStudiesResponse']['FullStudies'][0]['Study']['ProtocolSection']

    index2 = 0
    for value in protocolsection['ArmsInterventionsModule']['InterventionList']['Intervention']:
        for i in drug_dict:
            drug_dict[i.lower()]['DrugName'] = i.lower() 
            if i == value["InterventionName"].lower():
                DetectEntitiestext = value['InterventionDescription']
                test = (comprehend.detect_entities(Text=DetectEntitiestext, LanguageCode='en'))
                with open("ACdata" + str(index2)  +".json", 'w') as json_file:
                    
                    json.dump(test, json_file, sort_keys=True, indent=4)
                with open("ACdata" + str(index2)+".json", "r") as read_file:
                    index2= index2+1
                    data = json.load(read_file)
                    for i2 in range(len(data['Entities'])):
                        if(data['Entities'][i2]['Type'] == "QUANTITY"):
                            for k in range(len(amount)):
                                if (amount[k] in test['Entities'][i2]['Text']):
                                    drug_dict[i.lower()]['Dosage'] = test['Entities'][i2]['Text']
                        for j in range(len(time_label2)):
                            if time_label2[j] in data['Entities'][i2]['Text']:
                                drug_dict[i.lower()]['Duration'] = data['Entities'][i2]['Text']
    #print(drug_dict)
    comprehend_med = boto3.client(service_name='comprehendmedical')

    DetectEntitiestext = brief_description + detail_description
    result = comprehend_med.detect_entities(Text=DetectEntitiestext)
    i = 0
    with open("ACMdata" + str(i) +".json", 'w') as json_file:
        json.dump(result, json_file, sort_keys=True, indent=4)
        i = i + 1

    entities = result['Entities']
    for value in entities:
        try:
            for content in value['Attributes']:
                if content['RelationshipType'] == "FREQUENCY":
                    for content2 in drug_dict:
                        if value["Text"] in content2:
                            drug_dict[content2]['Duration'] = drug_dict[content2]['Duration'] +"("+ content['Text'] + ")"
        except KeyError as e:
            pass

    for arm in Arm_group:
        try:
            for DrugName in Arm_group[arm]['InterventionList']['ArmGroupInterventionName']:
                for DrugInList in drug_dict:
                    if DrugInList in DrugName.lower():
                        Arm_group[arm]['InterventionDescription'].append(drug_dict[DrugInList]) 
        except TypeError:
            pass
    for arm in Arm_group:
        try:
            for Drugidx in range(len(Arm_group[arm]['InterventionDescription'])):
                Arm_group[arm]['ArmGroupDescription'] = Arm_group[arm]['ArmGroupDescription'] + Arm_group[arm]['InterventionDescription'][Drugidx]['DrugName']  + ': '  +  Arm_group[arm]['InterventionDescription'][Drugidx]['Dosage'] + ' ' + Arm_group[arm]['InterventionDescription'][Drugidx]['Duration'] 
                Arm_group[arm]['ArmGroupDescription'] += ', '

        except KeyError:
            pass

    for key in Arm_group:
        InterventionDrug['ArmGroupList'].append(Arm_group[key])

    return (json.dumps(InterventionDrug, indent=4))

print(drug_time("https://www.clinicaltrials.gov/api/query/full_studies?expr=Placebo+Controlled+Double+Blind+Crossover+Trial+of+Metformin+for+Brain+Repair+in+Children+With+Cranial-Spinal+Radiation+for+Medulloblastoma&min_rnk=1&max_rnk=&fmt=json"))