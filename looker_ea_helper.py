import os, json
import looker_sdk
from looker_sdk import api_settings
from looker_sdk.sdk.api40 import models


class LookerEAHelperConfig:
    def __init__(self):
        self.explore_assistant_connection_name = None
        self.explore_assistant_dataset = None
        self.explore_assistant_examples_table = None
        self.explore_assistant_refinements_table = None
        self.explore_assistant_model_id = None
        self.lookml_model_name = None
        self.looker_explore_id = None

    @property
    def explore_key(self):
       return self.lookml_model_name + ":" + self.looker_explore_id
    
    @property
    def is_valid(self): # all are required
        for var in vars(self):
            if getattr(self, var) is None:
                return False

        return True



class MyApiSettings(api_settings.ApiSettings):
    def __init__(self, *args, **kw_args):
        super().__init__(*args, **kw_args)

    def read_config(self) -> api_settings.SettingsConfig:
        config = super().read_config()
        config["client_id"] = os.environ.get("LOOKER_ADMIN_CLIENT_ID")
        config["client_secret"] = os.environ.get("LOOKER_ADMIN_CLIENT_SECRET")
        config["base_url"] = os.environ.get("LOOKER_BASE_URL")
        config["verify_ssl"] = "true"

        return config


class LookerEAHelper:

    def __init__(self, config: LookerEAHelperConfig) -> None:
        if not config.is_valid:
            raise Exception('Invalid config: check values in passed LookerEAHelperConfig')
        
        self.sdk = looker_sdk.init40(config_settings=MyApiSettings())
        self.config = config

    def _run_sql_query(self, sql: str, raw_return:bool = False):
        sql_runner_query = self.sdk.create_sql_query(
        body=models.SqlQueryCreate(
            connection_id=self.config.explore_assistant_connection_name,
            sql=sql
        ))

        if not sql_runner_query.slug:
            return []

        result = self.sdk.run_sql_query(sql_runner_query.slug, 'json')

        return result if raw_return else json.loads(result)


    def _get_examples(self):
        sql = f"""
            SELECT
                explore_id
            , examples
            FROM {self.config.explore_assistant_dataset}.{self.config.explore_assistant_examples_table}
            WHERE explore_id = '{self.config.explore_key}'
        """

        results = self._run_sql_query(sql)

        if len(results) == 0:
            raise Exception(f"""No examples found for explore_key {self.config.explore_key} in 
                {self.config.explore_assistant_dataset}.{self.config.explore_assistant_examples_table}""")

        return json.loads(results[0]['examples'])


    def _get_example_prompts(self):
        examples = self._get_examples()

        def massager(item):
            return f'''input: "{item['input']}" ; output: {item['output']}'''

        return '\n'.join(list(map(massager , examples)))


    def _generate_full_prompt(self, prompt: str):
        semantic_model = self._get_semantic_model()
        explore_generation_examples = self._get_example_prompts()

        return f"""
            Context
            ----------

            You are a developer who would transalate questions to a structured Looker URL query based on the following instructions.

            Instructions:
                - choose only the fields in the below lookml metadata
                - prioritize the field description, label, tags, and name for what field(s) to use for a given description
                - generate only one answer, no more.
                - use the Examples (at the bottom) for guidance on how to structure the Looker url query
                - try to avoid adding dynamic_fields, provide them when very similar example is found in the bottom
                - never respond with sql, always return an looker explore url as a single string
                - response should start with fields= , as in the Examples section at the bottom

            LookML Metadata
            ----------

            Dimensions Used to group by information (follow the instructions in tags when using a specific field; if map used include a location or lat long dimension;):

            {semantic_model['dimensions']}

            Measures are used to perform calculations (if top, bottom, total, sum, etc. are used include a measure):

            {semantic_model['measures']}

            Example
            ----------

            {explore_generation_examples}

            Input
            ----------
            {prompt}

            Output
            ----------
        """

 
    def _get_semantic_model(self):

        def field_mapper(field: looker_sdk.sdk.api40.models.LookmlModelExploreField):
            result_pieces = []
            if field['name']:
                result_pieces.append('name: ' + field['name'])
            if field['type']:
                result_pieces.append('type: ' + field['type'])
            if field['label']:
                result_pieces.append('label: ' + field['label'])
            if field['description']:
                result_pieces.append('description: ' + field['description'])
            if field['tags'] and len(field['tags']):
                result_pieces.append('tags: ' + ' ,'.join(field['tags']))

            return ', '.join(result_pieces)

        explore_fields = self.sdk.lookml_model_explore(self.config.lookml_model_name, self.config.looker_explore_id, 'fields')
        dimensions = '\n'.join(list(map(field_mapper, explore_fields.fields.dimensions)))
        measures = '\n'.join(list(map(field_mapper, explore_fields.fields.measures)))

        return {

            'dimensions': dimensions,
            'measures': measures
        }


    def _generate_inference_sql(self, prompt: str):
        escaped_prompt = prompt.replace("\n","\\n").replace("'","\\'")
        subselect = f"SELECT '{escaped_prompt}' AS prompt"

        return f"""
            SELECT ml_generate_text_llm_result AS generated_content
            FROM
            ML.GENERATE_TEXT(
                MODEL `{self.config.explore_assistant_model_id}`, ({subselect}),
                STRUCT(
                0.05 AS temperature,
                1024 AS max_output_tokens,
                0.98 AS top_p,
                TRUE AS flatten_json_output,
                1 AS top_k
                )
            )"""


    def get_looker_return(self, prompt: str, result_format:str='sql'):
        allowed_result_formats = ["sql", "json", "png", "csv", "json-bi"]
        if result_format not in allowed_result_formats:
            raise Exception(f"LookerEAHelper.get_looker_return: result_format must be one of {allowed_result_formats}")

        full_prompt = self._generate_full_prompt(prompt)
        full_sql = self._generate_inference_sql(full_prompt)
        vertex_response = json.loads(self._run_sql_query(full_sql, raw_return=True))

        url_querystring = vertex_response[0]['generated_content'].strip()

        fields=[]
        pivots=[]
        filters={}
        sorts=[]

        parts = url_querystring.split('&')

        for part in parts:
            if part.startswith('fields'):
                fields = part.replace('fields=','').split(',')
            if part.startswith('pivots'):
                pivots = part.replace('pivots=','').split(',')
            if part.startswith('f['):
                key, value = part.replace('f[','').replace(']','').split('=')
                filters[key] = value
            if part.startswith('sorts'):
                sort_items = part.replace('sorts=','').split(',')
                for sort_item in sort_items:
                    sort_item_pieces = sort_item.split(' ')
                    sort_field = sort_item_pieces[0]
                    direction = ' desc' if sort_item_pieces[1] == 'desc' else ''
                    sorts.append(sort_field + direction)

        query = looker_sdk.models40.WriteQuery(
            fields=fields
            ,pivots=pivots
            ,model=self.config.lookml_model_name
            ,view=self.config.looker_explore_id
            ,filters=filters
            ,query_timezone='UTC'
        )

        return self.sdk.run_inline_query(body=query, result_format=result_format, cache=False)


