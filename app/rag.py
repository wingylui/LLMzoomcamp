from openai import OpenAI
from qdrant_client import QdrantClient, models
from api_key import openAI_api_key 

import json
from time import time


qd_client = QdrantClient("http://localhost:6333")
llm_client = OpenAI(api_key = openAI_api_key)

# ------------------------------ prompt template --------------------------------------
prompt_template = """
You are a helpful baking assistant. A client has asked the following question:

Client question:
{user_query}

Here are the top {number_of_results} potentially relevant recipes retrieved from the knowledge base:
{context_block}

Task:
- Choose the single most relevant document that best answers the client's question.
- Return the recipe from that document only.
- Do NOT combine multiple recipes together.
- Provide the recipe in natural human-readable format, including all of the following information:
    - Recipe name / title
    - Difficulty level
    - Ingredients list
    - Step-by-step instructions
    - Total cooking time in minutes
    - Calories (kcal)
- If none of the documents are relevant, respond: "I don’t have a recipe for that."

Provide your answer as a step-by-step baking recipe.
"""

result_template = """
"name"              :   {name},
"difficult"         :   {difficult},
"total_cooking_min" :   {total_cooking_min},
"kcal"              :   {kcal},
"ingredients"       :   {ingredients},
"steps"             :   {steps}
"""

def format_prompt(prompt_template, question, search_results):
    result_number = len(search_results)

    formatted_result = []
    for result in search_results:
        dum = result_template.format(**result).strip()
        formatted_result.append(dum)
        
    # joining the list of text into one block of text (seperated by ;;)
    context = ";;".join(formatted_result)
    prompt = prompt_template.format(user_query = question, number_of_results = result_number, context_block = context)

    return prompt.strip()
# ------------------------------ prompt template --------------------------------------

def llm_prompt(prompt,  model = "gpt-5-nano"):
    response = llm_client.chat.completions.create(
            model= model,
            messages=[{"role": "user", "content": prompt}]
        )
    
    result = response.choices[0].message.content # extract the results message out

    # extract the token used for this prompt
    usage = {
        "completion_tokens" : response.usage.completion_tokens,
        "prompt_tokens"     : response.usage.prompt_tokens,
        "total_tokens"      : response.usage.total_tokens
    }
    return result, usage


def rrf_description_search(query: str, limit: int = 1) -> list[models.ScoredPoint]:
    """
    searching for results
    using bm25 and jina (cosine similarity) combining two together which calculated by RRF
    will return the top 6 results
    """
    results = qd_client.query_points(
        collection_name="baking_recipes_description",
        prefetch=[
            models.Prefetch(
                query=models.Document(
                    text=query,
                    model="jinaai/jina-embeddings-v2-small-en",
                ),
                using="jina-v2",
                limit=(3 * limit),
            ),
            models.Prefetch(
                query=models.Document(
                    text=query,
                    model="Qdrant/bm25",
                ),
                using="bm25",
                limit=(3 * limit),
            ),
        ],
        # Fusion query enables fusion on the prefetched results
        query=models.FusionQuery(fusion=models.Fusion.RRF),
        with_payload=True,
    )


    search_results = []
    
    for point in results.points:
        search_results.append(point.payload)

    return search_results



def calculate_cost(usage, model):
    """
    usage: dict with keys "prompt_tokens" and "completion_tokens"
    """
    cost = 0

    if model == "gpt-5-nano":
        cost = (usage["prompt_tokens"] * 0.00005 + usage["completion_tokens"] * 0.0004) / 1000 # per 1k tokens
    elif model == "gpt-5-mini":
        cost = (usage["prompt_tokens"] * 0.00025 + usage["completion_tokens"] * 0.0020) / 1000 # per 1k tokens
    else:
        print(f"[Warning] Model '{model}' not recognized. Cost set to $0.")
    
    return cost


LLMeva_prompt_template = """
You are an evaluator for a RAG system.
Classify the generated answer’s relevance to the question as "NON_RELEVANT", "PARTLY_RELEVANT", or "RELEVANT".

Input:

Question: {question}

Answer: {llm_ans}

Output (JSON, no code block):

{{
  "Relevance": "NON_RELEVANT" | "PARTLY_RELEVANT" | "RELEVANT",
  "Explanation": "[Brief reason for classification]"
}}
"""

def llm_evaulation(question, ans_llm, model = "gpt-5-nano"):

    # reformat the prompt
    prompt = LLMeva_prompt_template.format(question= question, llm_ans = ans_llm)

    # LLM-as-a-judge
    response, usage = llm_prompt(prompt, model = model)
    try:
        evaluate = json.loads(response)
            # formatting for data storage
        result_js = {
            "question"      :   question,
            "llm_answer"    :   ans_llm,
            "relevance"     :   evaluate["Relevance"],
            "explanation"   :   evaluate["Explanation"]
        }
        return result_js, usage
    except json.JSONDecodeError:
        result_js = {"relevance": "UNKNOWN", "explanation": "Failed to parse evaluation"}
        return result_js, usage



def hybrid_description_rag(query, model_name = "gpt-5-nano"):
    t0 = time()

    search_results = rrf_description_search(query)
    prompt = format_prompt(prompt_template, query, search_results)
    answer, ans_usage = llm_prompt(prompt, model= "gpt-5-mini")

    evaluation_js, eva_usage  = llm_evaulation(query, answer, model= model_name)

    # calculating token cost
    ans_cost = calculate_cost(ans_usage, model_name)
    eva_cost = calculate_cost(eva_usage, model_name)
    total_cost = ans_cost + eva_cost

    # time used for processing this rag and llm prompt
    t1 = time()
    time_spent = t1 -t0

    # format output json
    result_js = {
        "question"              : query,
        "answer"                : answer,
        "model"                 : model_name,
        "time_spent"            : time_spent,
        "ans_completion_tokens" : ans_usage["completion_tokens"],
        "ans_prompt_tokens"     : ans_usage["prompt_tokens"],
        "ans_total_tokens"      : ans_usage["total_tokens"], 
        "eva_completion_tokens" : eva_usage["completion_tokens"],
        "eva_prompt_tokens"     : eva_usage["prompt_tokens"],
        "eva_total_tokens"      : eva_usage["total_tokens"], 
        "ans_cost"              : ans_cost,
        "eva_cost"              : eva_cost,
        "total_cost"            : total_cost,
        "relevance"             : evaluation_js["relevance"],
        "relevent_explain"      : evaluation_js["explanation"],
    }

    return result_js
