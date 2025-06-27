## AI_Agent to schedule and book appointments

### To run the Agent locally
#### Clone the repository to your local computer
- Install all the requirements using the command
```
pip install -r requirements.txt
```

- Now in new terminal 
```
uvicorn app.main:app --reload
```
- In another terminal 
```
streamlit run app\user_interface.py
```
