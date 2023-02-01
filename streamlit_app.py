import streamlit as st
# import streamlit_authenticator as stauth
import openai
from datetime import datetime
from streamlit.components.v1 import html
import pandas as pd
from pandasql import sqldf 
import re
import matplotlib.pyplot as plt
import seaborn as sns



st.set_page_config(page_title="Query Engine")

# Functions
def create_table_names_from_df(df):
    return('"' + '", "'.join([str(col) for col in df.columns])+'"')

verbose = True 

html_temp = """
                <div style="background-color:{};padding:1px">
                
                </div>
                """

with st.sidebar:
    st.markdown("""
    # About 
    A Query Engine is a tool to help you answer questions about your data. 

    Ask Data aims to empower everyone to understand their data. 
    """)
    st.markdown(html_temp.format("rgba(55, 53, 47, 0.16)"),unsafe_allow_html=True)
    st.markdown("""
    # Tips:
    Enter your table structure, upload a file, or try the demo dataset. 

    Then ask any questions you have about it, like you'd ask a team member. 
    """)
    st.markdown(html_temp.format("rgba(55, 53, 47, 0.16)"),unsafe_allow_html=True)
    st.markdown("""
    """,
    unsafe_allow_html=True,
    )

    query_type = st.radio(
        'Select an output preference',
        options=['Explore','SQL', 'Python', 'Brainstorm'])

    st.markdown("""
    For any questions, feedback, or inquiries, please reach out to [build@askdata.app](mailto:build@askdata.app)!""")

    


st.markdown("""
# Query Engine
""")

input_text_table, input_text_question, input_df_table = None, None, None

table_structure = ''

upload_tab, schema_tab, demo_tab = st.tabs(['Upload','Table Structure', 'Demo'])

@st.cache
def find_file_type_import(file):
    file_name = file.name
    # Total file extensions possible for importing data
    read_functions = {'csv': pd.read_csv,
                        'xlsx': pd.read_excel,
                        'txt': pd.read_csv,
                        'parquet': pd.read_parquet,
                        'json': pd.read_json}
    
    [df] = [read(file_name) for file_ext, read in read_functions.items() if file_name.endswith(file_ext)]

    return df

with upload_tab:
    print('Upload tab')
    uploaded_file = st.file_uploader("Choose your own CSV file")

    # if st.session_state.get("input_text_table") not in [None,""]:
    #     st.warning("To use your own data, clear the table structure in the Table Structure tab.")

    if uploaded_file is not None:   

        # upload_df = find_file_type_import(uploaded_file)
        # upload_df = pd.read_csv(uploaded_file)
        try:
            print('File attempted')
            upload_df = find_file_type_import(uploaded_file)
        except:
            st.warning('Perhaps try a different file type?')

        finally:
            print('File attempt finish')

        st.write(upload_df)
        table_structure = create_table_names_from_df(upload_df)
        prompt_prefix = f'Using a table named {uploaded_file.name}, with columns: '


with schema_tab: 

    if st.session_state.get("schema_tab") not in [None,""]:
        st.warning("To use your own data, clear the table structure in the Table Structure tab.")


    input_text_table = st.text_input("Enter your Table Structure", disabled=False, \
        placeholder="Example format: fact_table: (date, id, val), dim_table: (id, feat, qual)")
    
    if input_text_table:
        table_structure = input_text_table
        prompt_prefix = "Using a table structure: "

with demo_tab:
    st.markdown("""
    ### Example dataset: S&P 500 stock prices
    """)
    demofile_name = 'all_stocks_5yr'
    demofile_ext = '.csv'
    demo_df = pd.read_csv('data/'+demofile_name+demofile_ext)
    st.write(demo_df)
    if uploaded_file is None:
        if st.session_state.get("input_text_table") not in [None,""]:
            st.warning("To use the demo, clear the table structure in the Table Structure tab.")
        table_structure = create_table_names_from_df(demo_df)
        prompt_prefix = 'Using a table named "table", with columns: '


input_text_question = st.text_input("What would you like to ask your data?", disabled=False, \
    placeholder="Example: What is the weekly average val of feature?")


data_viz_prefix = '''
I want you to act as a scientific data visualizer. You will apply your knowledge of data science principles and visualization techniques to create compelling visuals that help convey complex information, develop effective graphs and maps for conveying trends over time or across geographies, utilize tools such as seaborn and matplotlib to design meaningful interactive dashboards, collaborate with subject matter experts in order to understand key needs and deliver on their requirements. We have a dataset df with columns : '''


if 'output' not in st.session_state:
    st.session_state['output'] = 0
  

def create_prompt(prompt_prefix ='', table_structure='', input_text_question=''):

    ## guess the category of data
    ## Guess how to handle it 
    ## try handlign it 

    if query_type == 'Explore':
        prompt_prefix = data_viz_prefix
        prompt_query = "Please create a visualization to find trends in this data using python seaborn or matplotlib code."
        prompt_suffix = 'import pandas as pd \nimport seaborn as sns \nimport matplotlib.pyplot as plt \ndf = pd.read_csv("data.csv") \n' 
        output_type = 'Explore'
        output_file_ext = '.md'

    elif query_type == 'SQL':
        prompt_query = "\n Write me a SQL query to to find: "
        prompt_suffix = '' 
        output_type = 'SQL'
        output_file_ext = '.sql'

    elif query_type == 'Python': 
        prompt_query = "\n You have a dataframe named df. Do not write an import or read file. Write me python code on the dataframe df using the pandas library to find: "
        prompt_suffix = 'import pandas as pd \n'
        output_type = 'Python'
        output_file_ext = '.py'


    elif query_type == 'Brainstorm':
        prompt_query = "What are some other things to explore in this data after finding "
        prompt_suffix = '\n Only return your top five ideas in a numbered list.'
        output_type = 'Text'
        output_file_ext = '.md'

    prompt = prompt_prefix \
             + str(table_structure) \
             + ' \n' \
             + prompt_query \
             + str(input_text_question) \
             + ' \n' \
             + prompt_suffix 

    return prompt, output_type, output_file_ext

## Prompter 


if (len(table_structure) > 5) and (len(input_text_question) > 5):

    st.session_state['output'] = st.session_state['output'] + 1

    prompt, output_type, output_file_ext = create_prompt(table_structure=table_structure)

    if verbose:
        st.write(prompt)

    if prompt:

        openai.api_key = st.secrets["openaiKey"]
        with st.spinner('Thinking...'):
            try:
                response = openai.Completion.create(engine="text-davinci-002", prompt=prompt, max_tokens=1000, temperature=0.3, top_p=1, frequency_penalty=0.0, presence_penalty=0.0)


                question_output = response['choices'][0]['text']
                today = datetime.today().strftime('%Y-%m-%d')
                topic = "Query help for: "+input_text_question+"\n@Date: "+str(today)+"\n"+question_output

                if query_type == "Brainstorm":
                    question_output.replace('-','\n-')
                st.info(question_output)

                filename = "query_"+str(st.session_state['output'])+"_"+str(today)+ output_file_ext

                btn = st.download_button(
                    label="Download " + output_type,
                    data=topic,
                    file_name=filename
                )

                # Evaluate the output 
                df = upload_df if uploaded_file is not None else demo_df

                explainer_prompt_prefix = "Please explain what the following code does: \n"
                explainer_prompt = explainer_prompt_prefix + question_output + "\n"


                if query_type == 'Python' or query_type == 'Explore':
                    try:
                        
                        lines = question_output.splitlines()
                        for line in lines:
                        # question_output.replace('\n','\n\n')
                            eval_check = eval(line)
                            st.write(eval_check)
                        explanation_response = openai.Completion.create(engine="text-davinci-002", prompt=explainer_prompt, max_tokens=1000, temperature=0.3, top_p=1, frequency_penalty=0.0, presence_penalty=0.0)
                        explanation_output = explanation_response['choices'][0]['text']
                        st.markdown("### Explanation")
                        st.write(explanation_output)
                    except Exception as e:
                        if verbose:
                            st.write(e)
                        pass

                elif query_type == 'SQL':
                    try:
                        pysqldf = lambda q: sqldf(q, globals())
                        re_table_name = re.compile('FROM (\w*)', re.IGNORECASE)

                        sql_string = re_table_name.sub('FROM df', question_output)

                        explanation_response = openai.Completion.create(engine="text-davinci-002", prompt=explainer_prompt, max_tokens=1000, temperature=0.3, top_p=1, frequency_penalty=0.0, presence_penalty=0.0)
                        explanation_output = explanation_response['choices'][0]['text']
                        
                        st.markdown("### Explanation")
                        st.write(explanation_output)

                        if verbose:
                            st.write(sql_string)
                        pass
                    
                        st.write(pysqldf(sql_string))
                    except Exception as e:
                        if verbose:
                            st.write(e)
                        pass

            except openai.error.RateLimitError:
                st.error("Sorry, there are many requests at the moment! Please try again in a few minutes.")
            finally:
                pass 
            ## with tokens to spare, could shorten input text 

elif query_type == 'Explore':

    prompt, output_type, output_file_ext = create_prompt()

    if verbose:
        st.write(prompt)
        
        
    # with st.spinner('Thinking...'):
        # response = openai.Completion.create(engine="text-davinci-002", prompt=prompt, max_tokens=1000, temperature=0.3, top_p=1, frequency_penalty=0.0, presence_penalty=0.0)

        # question_output = response['choices'][0]['text']
        # today = datetime.today().strftime('%Y-%m-%d')
        # topic = "Query help for: "+input_text_question+"\n@Date: "+str(today)+"\n"+question_output

        # st.info(question_output)