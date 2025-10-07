import json
import uuid
import os
from qdrant_client import QdrantClient, models


DATA_PATH = os.getenv("DATA_PATH", "../data/baking_cleaned.json")


def main (path = DATA_PATH):
    with open (path, "r") as f:
        baking_recipes = json.load(f)

    client = QdrantClient("http://localhost:6333")
    qd_ingestion(baking_recipes, client)



def qd_ingestion(new_recipes, qd_client):
    # --------------------------------- adding points -------------------------------
    points_vector = []
    for recipe in new_recipes:
        ingred = ";".join(recipe["ingredients"]) # joining list of text to a block of text
        txt = recipe["name"] + " | " + recipe["difficult"] + " | " + recipe["dish_type"] + " | " + recipe["description"] + " | " + ingred 
        point = models.PointStruct(
            id = recipe["id"],
            
            vector = {
                "jina-v2": models.Document(
                        text = txt,
                        model ="jinaai/jina-embeddings-v2-small-en",
                    ),
                "bm25": models.Document(
                        text = txt, 
                        model ="Qdrant/bm25",
                    )
            },

            payload = {
                "id"                :   recipe["id"],
                "name"              :   recipe["name"],
                "dish_type"         :   recipe["dish_type"],
                "difficult"         :   recipe["difficult"],
                "ingredients"       :   recipe["ingredients"],
                "steps"             :   recipe["steps"],
                "preparation_min"   :   recipe['prep_mins'], 
                "cooking_min"       :   recipe['cook_mins'], 
                "total_cooking_min" :   recipe["total_mins"],
                "kcal"              :   recipe['kcal'], 
                "fat"               :   recipe['fat'], 
                "saturated fat"     :   recipe['saturates'], 
                "carbohydrates"     :   recipe['carbs'], 
                "sugars"            :   recipe['sugars'], 
                "fibre"             :   recipe['fibre'], 
                "protein"           :   recipe['protein'], 
                "salt"              :   recipe['salt'],
                "rating"           :   recipe["rattings"]
            }         
        )

        points_vector.append(point)
    # --------------------------------- adding points -------------------------------



    # update the new data to client
    qd_client.upsert(
        collection_name="baking_recipes_description",
        points = points_vector 
    )

main(DATA_PATH)