# AI-Challenge (CSIT track)

Hi! We are ghetto hackers, and we would like to present to you our LLM-powered software FoodBot!

FoodBot is your typical food enthusiast and nutritionist in Singapore. While he has tremendous knowledge of food around Singapore, he is constantly looking out for your health and making sure that you are eating healthy, but at the same time having the privilege to choose from a variety of food options. If you are not sure of what to eat, do tell FoodBot what you are craving/what your health conditions are/any type of food that you would prefer, and he will give you a handful of options to choose from!

## Description of software and LLM

FoodBot was developed with Google's PaLM2 as our LLM, Python's Flask as our backend, and Javascript and HTML as our frontend. 

We have also incorporated a vector database (chromadb) to store a [dataset](https://www.kaggle.com/datasets/polartech/16000-grab-restaurants-in-singapore/discussion) of over 16000 restaurants from all over Singapore. The vector database passes each data through an embedding layer and stores each data as a point in the vector space. When we query the vector database, the vector database will output the data that are the most relevant to the query.

To make the result more personalised, we utilised the google maps API to decode the approximate coordinates of where the user would like to eat. Then, we search all the restaurants in the database that are within a 2km radius of the user's preferred location.

Of course, we greatly improved our LLM through prompt engineering techniques such as few-shot prompting and chain of thought, where we guide the LLM through example user prompts, expected outputs and the reasons behind them. Prompt engineering can shape responses in certain formats such as json formats, which facilitates data transfer in the backend.

## How to run the code

1. Run ```pip install -r requirements.txt```
2. Run all the cells in the ```import_data.ipynb``` file. This will take quite a while, as we are adding the data (and metadata) from the dataset into the vector database.
3. Once done, you can run ```python3 code/app.py``` to activate the frontend and backend locally.
