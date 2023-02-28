from wit import Wit 

wit_access_token = "RA4GY2554MC3AJBZ42HC57LSK2IGYKB2"
client = Wit(access_token = wit_access_token)

def wit_response(message_text):
    resp = client.message(message_text)
    
    entity = None
    value = None
    confidence = None
    
    try:
        entity = list(resp['entities'])[1]
        confidence = resp['entities'][entity][0]['confidence']
        value = resp['entities'][entity][0]['value']
    except:
        pass
    
    return (entity, confidence, value, resp)
