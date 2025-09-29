from query_enhancement.enhance import query_enhancer
from store_in_vector_db.vector_db import query_documents
from generate_sql.sql import sql_generator
from retrieve_data_from_db.postgres_db import retrieve_data_from_postgres
from create_plots.plots import create_csv_async
from final_ans.final_llm_call import get_ans_with_relevant_data

import asyncio
import json



def cleaned_response(res):
    return json.loads(res)



def sql_to_ans(enhanced_query, history, vector_float_ids=None):

    generated_sql_response = sql_generator(enhanced_query, vector_float_ids)
    print("Generated SQL response : ", generated_sql_response, end="\n\n\n")

    if(generated_sql_response.get('sql_query') != None):
        sql_query = generated_sql_response['sql_query']

    else:
        print("\n\n\n", '--- SQL GENERATION LO ISSUE --- ', end="\n\n\n")
        return
    
    if(generated_sql_response.get('sources_to_cite') != None):
        sources_to_cite = generated_sql_response['sources_to_cite']

    else:
        print("\n\n\n", '--- SQL GENERATION LO ISSUE --- ', end="\n\n\n")
        return

    pg_data = retrieve_data_from_postgres(sql_query)
    # print("PG_DATA : ", pg_data, end="\n\n\n")

    suggest_plot=False
    if(generated_sql_response.get('suggest_plot') != None and generated_sql_response['suggest_plot']):
        if(generated_sql_response.get('suggest_plot')):
            suggest_plot = generated_sql_response['suggest_plot']
        csv_url =  asyncio.run(create_csv_async(pg_data))

    pg_data = pg_data.to_json(orient="records")


    ans = cleaned_response(get_ans_with_relevant_data(enhanced_query, pg_data, history, sources_to_cite, suggest_plot, csv_url))
    print("Final Response : ", ans, end = "\n\n\n")

    return ans



def query_to_answer(query, history):

    history.append({"question" : query})


    # ------------ QUERY EHNANCEMENT ------------- #
    query_enhancer_response = cleaned_response(query_enhancer(query, history))
    print("Enhanced query response : ",query_enhancer_response, end="\n\n\n")


    if(query_enhancer_response.get('need_retrieval') != None and query_enhancer_response.get('only_sql') != None):
        need_retrieval = query_enhancer_response['need_retrieval']
        only_sql = query_enhancer_response['only_sql']

        
        
        if(query_enhancer_response.get('enhanced_query') != None):
            enhanced_query = query_enhancer_response['enhanced_query']
        else:
            enhanced_query = query


        
        
        # ---- QUERY WHICH DOESN'T REQUIRE ANY VECTOR / DB SEARCH ---- #
        if(not need_retrieval and not only_sql and query_enhancer_response.get('reply') != None):
            ans = {
                "answer": query_enhancer_response['reply'],
                "csv_url": None,
                "plot_type": None,
                "plot_heading": None,
                "sources_to_cite": None
            }
        






        # ---- QUERY WHICH REQUIRES ONLY DB SEARCH ---- #
        elif(not need_retrieval and only_sql):

            
            # ------------ SQL QUERY TO FINAL ANS ------------- #   
            ans = sql_to_ans(enhanced_query, history)
        







        # ---- QUERY WHICH REQUIRES BOTH VECTOR & DB SEARCH ---- #
        elif(need_retrieval):
            filters = {}
            if(query_enhancer_response.get('where') != None and query_enhancer_response['where'] != {}):
                filters = query_enhancer_response['where']
            


            # ------------ VECTOR DB DATA RETRIVAL ------------- #
            vector_data = query_documents(enhanced_query, filters)
            vector_ids = vector_data['ids'][0]
            print(vector_ids)



            # ------------ SQL QUERY TO FINAL ANS ------------- #
            ans = sql_to_ans(enhanced_query, history, vector_ids)




    else:
        print("\n\n\n", '--- QUERY ENHANCEMENT LO ISSUE UNDI CHUDU --- ', end="\n\n\n")
        return 

    history[-1]["answer"] = ans["answer"]

    return ans, history


