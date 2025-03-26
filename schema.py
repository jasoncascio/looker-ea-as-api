
########### Input ###########
input_schema = {
  "type": "object",
  "properties": {
    "lookml_model_name": {
      "type": "string",
      "description": "This is the looker model name.",
      "default": "thelook"
    },
    "looker_explore_id": {
      "type": "string",
      "description": "This is the looker_explore_id.",
      "default":"the_look"
    },
    "user_prompt": {
      "type": "string",
      "description": "This is the text that defines what the user is asking for."
    },
    "return_format": {
      "type": "string",
      "description": "This is the return format for the call. sql will return raw sql. json will return a json formatted string of data. png will return a png image.",
      "enum": [
        "sql",
        "json",
        "png"
      ],
      "default": "json"
    }
  },
  "required": [
    "user_prompt"
  ]
}

input_example = {
  "lookml_model_name":"thelook",
  "looker_explore_id":"order_items",
  "user_prompt":"Count of accessory orders by date for the last 4 days line chart",
  "result_format":"json"
}


########### Output ###########
output_schema = {
    "type": "object",
    "properties": {
        "error_message": {
            "type": "string",
            "description": "This is an error message coming from the API. It will be null if there is no error.",
            "default": ""
        },
        "return_data": {
            "type": "object",
            "description": "This is the content-type and raw data returned from the API.",
            "properties": {
                "content_type": {
                    "type": "string",
                    "description": "This is the content-type of the data being returned from the API",
                    "enum": [
                        "sql",
                        "json",
                        "json-bi",
                        "csv",
                        "png"
                    ],
                },
                "data": {
                    "type": "string",
                    "description": "This is the raw data being returned from the API.",
                    "default": ""
                }
            }
        },
        "request": {
            "type": "object",
            "description": "This is the request object that was sent to the API.",
        }
    }
}

output_example = {
  "error_message": "",
  "return_data": {
    "content_type": "json",
    "data": [
      {
        "products.category": "Accessories",
        "order_items.created_date": "2025-03-25",
        "order_items.count": 15
      }
    ]
  },
  "request_object": {
    "lookml_model_name": "thelook",
    "looker_explore_id": "order_items",
    "user_prompt": "Count of accessory orders by date for the last day",
    "result_format": "json"
  }
}