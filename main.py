import functions_framework
from flask import Response
import json

from .looker_ea_helper import LookerEAHelperConfig, LookerEAHelper


### Constants ###
EXPLORE_ASSISTANT_CONNECTION_NAME = "looker-private-demo"
EXPLORE_ASSISTANT_DATASET = "explore_assistant"
EXPLORE_ASSISTANT_EXAMPLES_TABLE = "explore_assistant_examples"
EXPLORE_ASSISTANT_REFINEMENTS_TABLE = "explore_assistant_refinement_examples"
EXPLORE_ASSISTANT_MODEL_ID = "jc-looker.cortex_pso_explore_assistant.explore_assistant_llm"


class ReturnObject:
    def __init__(self):
        self.error_message = ""
        self.content_type = ""
        self.data = ""
        self.request_object = ""

    def to_dict(self):
        return {
            "error_message": self.error_message,
            "return_data": {
                "content_type": self.content_type,
                "data": self.data
            },
            "request_object": self.request_object         
        }


@functions_framework.http
def main(request):

    ### Initialize Return Object ###
    return_object = ReturnObject()

    ### Handle inputs from Request
    try:
        request_json = request.get_json(silent=True)
        return_object.request_object = request_json

        ### lookml_model_name
        lookml_model_name = request_json.get("lookml_model_name")
        if not lookml_model_name:
            raise Exception("lookml_model_name is required")
        
        ### looker_explore_id
        looker_explore_id = request_json.get("looker_explore_id")
        if not looker_explore_id:
            raise Exception("looker_explore_id is required")
        
        ### user_prompt
        user_prompt = request_json.get("user_prompt")
        if not user_prompt:
            raise Exception("user_prompt is required")
        
        ### return_format
        return_format = request_json.get("return_format")
        acceptable_return_formats = ["sql", "json", "png", "csv", "json-bi"]
        if return_format and return_format not in acceptable_return_formats:
            raise Exception(f"return_format must be one of {acceptable_return_formats}")
        if not return_format :
            raise Exception("return_format is required")
        return_object.content_type = return_format
        
        
    except Exception as e:
        return_object.error_message = str(e)

        return Response(json.dumps(return_object.to_dict()), status=400, content_type='application/json')


    ### Do the thing
    try:
        ### Configure Connection & Connect ###
        config = LookerEAHelperConfig()
        config.explore_assistant_connection_name = EXPLORE_ASSISTANT_CONNECTION_NAME
        config.explore_assistant_dataset = EXPLORE_ASSISTANT_DATASET
        config.explore_assistant_examples_table = EXPLORE_ASSISTANT_EXAMPLES_TABLE
        config.explore_assistant_refinements_table = EXPLORE_ASSISTANT_REFINEMENTS_TABLE
        config.explore_assistant_model_id = EXPLORE_ASSISTANT_MODEL_ID
        config.lookml_model_name = lookml_model_name
        config.looker_explore_id = looker_explore_id
        
        looker_ea_helper = LookerEAHelper(config)
        return_object.data = json.loads(looker_ea_helper.get_looker_return(user_prompt, return_format))
        
        return Response(json.dumps(return_object.to_dict()), status=200, content_type='application/json')
        

    except Exception as e:
        return_object.error_message = str(e)

        return Response(return_object.to_dict(), status=500)