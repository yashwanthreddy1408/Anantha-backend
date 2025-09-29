from query_enhancement.enhance import query_enhancer
import json
import asyncio
from store_in_vector_db.vector_db import query_documents
from generate_sql.sql import sql_generator
from retrieve_data_from_db.postgres_db import retrieve_data_from_postgres
from final_ans.final_llm_call import get_ans_with_relevant_data


# get user query
# enhance it
# retrieve vectors

# ---


# query = input("Enter you query : ")


def clean_response(res):
    return json.loads(res)


def get_enhanced_response(query, history):

    history.append({"question": query})


    enhanced_query = query_enhancer(query, history)
    print(enhanced_query)
    response = clean_response(enhanced_query)



    # print("Response : ", response)
    
    if(isinstance(response, dict) and response.get('need_retrieval') != None and response['need_retrieval'] and response.get('enhanced_query') != None):

        # print("\nEnhanced Query : ", response["enhanced_query"], end="\n")
        # print("\nFilters : ", response["where"], end="\n")
        print("Response : ", response)

        filters = {}
        if(response.get('where') != None and response['where'] != {}):
            filters = response['where']


        retrieved_vectors = query_documents(response['enhanced_query'], filters)

        # print()
    
        generated_sql = sql_generator(enhanced_query, retrieved_vectors)

        print(generated_sql)

        data = retrieve_data_from_postgres(generated_sql)

        data = data.to_json(orient="records")

        print(data[:100])

        ans = get_ans_with_relevant_data(enhanced_query, data, history)

        print(ans)
        
        # history[-1]["answer"] = ans

    elif(isinstance(response, dict) and response.get('reply') != None):
        ans = response['reply']
        
    else:
        ans = response

    history[-1]['answer'] = ans


    return ans, history

history = []
ans, history = get_enhanced_response(input('>'), [])

print(ans)

