import os

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/etc/secrets/firebase-creds.json"




from fastapi import FastAPI,Request,Query,Form
from fastapi.responses import HTMLResponse,RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import google.oauth2.id_token
from google.auth.transport import requests
from google.cloud import firestore,storage
from google.cloud.firestore_v1.base_query import FieldFilter
import starlette.status as status
import local_constants
from datetime import datetime

app=FastAPI() 

firestore_db=firestore.Client()

firebase_request_adapter = requests.Request()

app.mount('/static',StaticFiles(directory='static'),name='static')
templates=Jinja2Templates(directory="templates")

def validateFirebaseToken(id_token):
    if not id_token:
        return None
    user_token = None
    try:
        user_token=google.oauth2.id_token.verify_firebase_token(id_token,firebase_request_adapter)   
    except ValueError as err:
        print(str(err))
    return user_token

async def getUserTweetsByFollowing(user_id):
    userData = firestore_db.collection("User").document(user_id)
    user_data = userData.get().to_dict()
    followingList = user_data.get("following", [])

    tweetsFromFollowing = []
    for following_username in followingList:
        tweetData = firestore_db.collection("Tweet").where("username", "==", following_username).get()
        for tweet_doc in tweetData:
            tweetsFromFollowing.append(tweet_doc.to_dict())

    tweetData = firestore_db.collection("Tweet").where("userId", "==", user_id).get()
    tweetsFromUserId = [tweet_doc.to_dict() for tweet_doc in tweetData]

    mergedTweets = tweetsFromFollowing + tweetsFromUserId

    mergedTweets.sort(key=lambda x: x['date'], reverse=True)

    last20Tweets = mergedTweets[:20]

    return last20Tweets


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)
    
    if user_token:
        userCollection = firestore_db.collection('User').document(user_token['user_id'])
        TweetCollection = firestore_db.collection('Tweet').document()

        user_doc = userCollection.get()
        
        if user_doc.exists:
            userTweets = None
            UserName = get_username(user_token.get("user_id"))
            current_tweets = await getUserTweetsByFollowing(user_token['user_id']) 
            
            return templates.TemplateResponse('main.html', {'request': request, 'user_token': user_token, 'error_message': None,'user_info': userTweets,'UserName': UserName,"AllTweets":current_tweets})
        else:
            user_names = getAllUsernames()
            print(user_names,"user_names")
            return templates.TemplateResponse('userName.html', {'request': request, 'user_token': user_token,"user_names":user_names})
    else:
        return templates.TemplateResponse('main.html', {'request': request, 'user_token': None, 'error_message': None})


@app.get("/setUsername", response_class=HTMLResponse)
async def root(request: Request):
    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)

    if not user_token:
      
        return templates.TemplateResponse('main.html', {'request': request, 'user_token': None, 'error_message': None})
    else:
        user_names = getAllUsernames()
        return templates.TemplateResponse('userName.html', {'request': request, 'user_token': user_token, 'error_message': None,"user_names":user_names})


@app.post("/updateUserName", response_class=RedirectResponse)
async def update_username(request: Request):
    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)
    form = await request.form()
    
    if user_token:
        user_id = user_token.get("user_id")  
        username_query = firestore_db.collection("User").where("username", "==", form["newUsername"]).get()
        if len(username_query) > 0:
                duplicateCheck = "Username already exists"
                return templates.TemplateResponse('userName.html', {'request': request, 'user_token': user_token, 'error_message': duplicateCheck})
        else:
            userName = {
                "username": form["newUsername"],
                "userEmail": user_token["email"]
            }
            firestore_db.collection("User").document(user_id).set(userName)

            return RedirectResponse("/", status_code=status.HTTP_302_FOUND)
    else:
       print("User token is invalid")
    
    return RedirectResponse("/", status_code=status.HTTP_302_FOUND)

def get_username(user_id):
    user_doc_ref = firestore_db.collection("User").document(user_id)
    user_doc = user_doc_ref.get()

    if user_doc.exists:
        user_data = user_doc.to_dict()
        return user_data.get("username")
    else:
        return None

def getTweetsByUserId(user_id):
    tweets_query = firestore_db.collection("Tweet").where("userId", "==", user_id).get()

    tweets_data = []
    
    for tweet in tweets_query:
        tweet_data = tweet.to_dict()
        tweets_data.append(tweet_data)
        tweets_data.sort(key=lambda x: x['date'], reverse=True)
    return tweets_data

@app.get("/addTweet", response_class=HTMLResponse)
async def addTweet(request: Request):
    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)
    if not user_token:
       
        return templates.TemplateResponse('main.html', {'request': request, 'user_token': None, 'error_message': None})
    else:

        return templates.TemplateResponse('addTweet.html', {'request': request, 'user_token': user_token, 'error_message': None})


@app.post("/updateTweet", response_class=RedirectResponse)
async def update_username(request: Request):
    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)
    form = await request.form()
    tweetImage = form.get("tweetImage")
    print("tweetImage",tweetImage)
    if user_token:
        storage_client = storage.Client(project=local_constants.PROJECT_NAME)
        bucket = storage_client.bucket(local_constants.PROJECT_STORAGE_BUCKET)
        if tweetImage and tweetImage.filename:

            print(form.get("tweetImage"),"99999999999999999999")
            addFile(form.get("tweetImage"))

            filename = form.get("tweetImage").filename  
            matchingUrl = None

            print("form.get(tweetImage)",form.get("tweetImage").filename)
            imageUrls = []
            blobs = blobList(None)
            for blob in blobs:
                # print("heyyyyyyyyyyyyyyyyyyyyyyyyy",blob.name)
                url = f"https://storage.googleapis.com/{local_constants.PROJECT_STORAGE_BUCKET}/{blob.name}"
                print(url)
                imageUrls.append(url)


            print(imageUrls,"vinayyyy")
           

            for url in imageUrls:
                if filename in url:
                    matchingUrl = url
                    break

        else:
            matchingUrl = None    



        user_id = user_token.get("user_id")
        newTweet = form.get("newTweet")
        tweetDocRef = firestore_db.collection("Tweet").document()
        tweet_data = {
            "username": get_username(user_token.get("user_id")),
            "userEmail": user_token["email"],
            "userId": user_id,
            "tweetContent": newTweet,
            "date":datetime.now(),
             "tweetId": tweetDocRef.id,
             "imageUrl":matchingUrl
        }
        print("tweet_datavvvvvvvv",tweet_data)
        tweetDocRef.set(tweet_data)

        user_doc_ref = firestore_db.collection("User").document(user_id)
        user_doc = user_doc_ref.get()

        if user_doc.exists:
            user_data = user_doc.to_dict()
            current_tweets = user_data.get("tweets", [])
            current_tweets.append({
                "tweetContent": newTweet,
                "tweetId": tweetDocRef.id,
                "imageUrl":matchingUrl
            })

            user_doc_ref.update({"tweets": current_tweets})
            return RedirectResponse("/", status_code=status.HTTP_302_FOUND)
        else:
            print("User document does not exist")

    else:
        print("User token is invalid")
    
    return RedirectResponse("/", status_code=status.HTTP_302_FOUND)





@app.post("/filter-by-string", response_class=RedirectResponse)
async def filter_by_string(request: Request, search_input: str = Form(default=""), filter_criteria: str = Form(default="")):
    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)
    
    if user_token:
        user_id = user_token.get("user_id")
        filteredUser = []
        filteredTweet = []
        if not filter_criteria:

            return RedirectResponse("/",status_code=status.HTTP_302_FOUND)
        
        if filter_criteria == "username":
                    users_query = firestore_db.collection("User").where("username", ">=", search_input.lower()).where("username", "<=", search_input + u'\uf8ff').get()
                    for user in users_query:
                        user_data = user.to_dict()
                        filteredUser.append({"username": user_data["username"], "userEmail": user_data["userEmail"]})

        elif filter_criteria == "tweetContent":
                    tweets_query = firestore_db.collection("Tweet").where("tweetContent", ">=", search_input).where("tweetContent", "<=", search_input + u'\uf8ff').get()
                    for tweet in tweets_query:
                        tweet_data = tweet.to_dict()
                        user_date = tweet_data["date"]  
                        formatted_date = user_date.strftime("%B %d, %Y %I:%M %p")
                        filteredTweet.append({"username": tweet_data["username"], "tweetContent": tweet_data["tweetContent"], "date": formatted_date, "userEmail": tweet_data["userEmail"],"imageUrl": tweet_data["imageUrl"]})
        UserName = get_username(user_token.get("user_id"))

        return templates.TemplateResponse('main.html', {'request': request,'user_token': user_token,'error_message': 'no error here','user_info': filteredUser,'user_tweet':filteredTweet,"UserName":UserName})
            
    else:
        print("User token is invalid")
        return RedirectResponse("/", status_code=status.HTTP_302_FOUND)

def getAllUsernames():
    usernames = []
    users_query = firestore_db.collection("User").get()
    for user_doc in users_query:
        user_data = user_doc.to_dict()
        username = user_data.get("username")
        if username:
            usernames.append(username)
    print(usernames,"usernamesusernames")
    return usernames

def getuserProfile(username):
    tweets_query = firestore_db.collection("Tweet").where("username", "==", username).order_by("date", direction=firestore.Query.DESCENDING).limit(10).get()

    tweets_data = []    
    userEmail = None
    userUsername = None
    imageURL = None
    for tweet in tweets_query:
        tweet_data = tweet.to_dict()

        tweets_data.append({
            'tweetContent': tweet_data['tweetContent'],
            'date': tweet_data['date'].strftime("%Y-%m-%d %H:%M:%S"),
            'imageURL': tweet_data.get('imageUrl')
        })
       
        if userEmail is None and userUsername is None:
            userEmail = tweet_data.get('userEmail')
            userUsername = tweet_data.get('username')
    
    return {
        'userEmail': userEmail,
        'username': userUsername,
        'tweets': tweets_data
    }



@app.get("/userProfile", response_class=HTMLResponse)
async def userProfile(request: Request, username: str = Query(...)):
    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)
    follow_status = ""  

    if user_token:
        user_doc_ref = firestore_db.collection("User").document(user_token["user_id"])
        user_data = user_doc_ref.get().to_dict()
        followingList = user_data.get("following", [])
        if username in followingList:
            follow_status = "Unfollow"
        else:
            follow_status = "Follow"

        tweets_query = firestore_db.collection("User").where("username", "==", username).get()
        for tweet in tweets_query:
            tweet_data = tweet.to_dict()
            # userEmail = tweet_data.get('userEmail')
        print(tweet_data.get('userEmail'),"tweets_queryrrrrrrrrrrrrr")
        Username  = username
        print("22222222222",user_token["email"])

        if tweet_data.get('userEmail') == user_token["email"]:
            same_username = True
        else:
            same_username = False


        userdata = getuserProfile(username)
        return templates.TemplateResponse('userProfile.html', {'request': request, 'user_token': user_token, 'error_message': None, 'user_info': userdata, 'follow_status': follow_status,"same_username":same_username})
    else:
        return templates.TemplateResponse('main.html', {'request': request, 'user_token': None, 'error_message': None})


@app.post("/follow-unfollow")
async def follow_unfollow(request: Request):
    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)
    follow_status = ""
    if user_token:
        form = await request.form()
        action = form.get("action")
        targetUsername = form.get("targetUsername")
        userdata = getuserProfile(targetUsername)

        if action == "follow":
            user_doc_ref = firestore_db.collection("User").document(user_token.get("user_id"))
            user_data = user_doc_ref.get().to_dict()
            followingList = user_data.get("following", [])
            if targetUsername not in followingList:
                followingList.append(targetUsername)
                user_doc_ref.update({"following": followingList})
                follow_status = "Unfollow" 
            user_id = user_token.get("user_id")
            user_doc = firestore_db.collection("User").document(user_id).get()
            if user_doc.exists:
                userUsername = user_doc.to_dict().get("username")
                target_user_doc_ref = firestore_db.collection("User").where("username", "==", targetUsername).limit(1).get()
                for doc in target_user_doc_ref:
                    target_user_data = doc.to_dict()
                    followers_list = target_user_data.get("followers", [])
                    if userUsername not in followers_list:
                        followers_list.append(userUsername)
                        firestore_db.collection("User").document(doc.id).update({"followers": followers_list})

        elif action == "unfollow":
            user_doc_ref = firestore_db.collection("User").document(user_token.get("user_id"))
            user_data = user_doc_ref.get().to_dict()
            followingList = user_data.get("following", [])
            if targetUsername in followingList:
                followingList.remove(targetUsername)
                user_doc_ref.update({"following": followingList})
            follow_status = "Follow"
            user_id = user_token.get("user_id")
            user_doc = firestore_db.collection("User").document(user_id).get()
            if user_doc.exists:
                userUsername = user_doc.to_dict().get("username")
                target_user_doc_ref = firestore_db.collection("User").where("username", "==", targetUsername).limit(1).get()
                for doc in target_user_doc_ref:
                    target_user_data = doc.to_dict()
                    followers_list = target_user_data.get("followers", [])
                    if userUsername in followers_list:
                        followers_list.remove(userUsername)
                        firestore_db.collection("User").document(doc.id).update({"followers": followers_list})

    else:
        print("User token is invalid")

    return templates.TemplateResponse('userProfile.html', {'request': request,'user_token': user_token,'error_message': 'no error here','user_info': userdata,'follow_status': follow_status})

def getDatabyID(tweetID):
    doc_ref = firestore_db.collection("Tweet").document(tweetID)
    doc = doc_ref.get()
    
    if doc.exists:
        return doc.to_dict()
    else:
        return None



@app.get("/editTweet", response_class=HTMLResponse)
async def editTweet(request: Request, tweetID: str = Query(...)):
    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)

    if user_token:
        userdata = getDatabyID(tweetID)
        return templates.TemplateResponse('editTweet.html', {'request': request, 'user_token': user_token, 'error_message': None,"userdata":userdata})
    else:
        return templates.TemplateResponse('main.html', {'request': request, 'user_token': None, 'error_message': None})


@app.post("/deleteTweet", response_class=RedirectResponse)
async def deleteTweet(request: Request):
    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)
    form = await request.form()
    
    if user_token:
        try:
            tweet_id = form["tweetId"]
     
            firestore_db.collection("Tweet").document(tweet_id).delete()
            
            user_doc_ref = firestore_db.collection("User").document(user_token["user_id"])
            user_doc = user_doc_ref.get()

            if user_doc.exists:
                user_data = user_doc.to_dict()
                current_tweets = user_data.get("tweets", [])

                updated_tweets = [tweet for tweet in current_tweets if tweet.get("tweetId") != tweet_id]

                user_doc_ref.update({"tweets": updated_tweets})

            UserName = get_username(user_token.get("user_id"))
            current_tweets = await getUserTweetsByFollowing(user_token['user_id']) 
            return templates.TemplateResponse('main.html', {'request': request, 'user_token': user_token, 'error_message': None, 'UserName': UserName, "AllTweets": current_tweets})
        
        except Exception as e:
            return RedirectResponse("/", status_code=status.HTTP_302_FOUND)
    
    else:
        print("User token is invalid")
        return RedirectResponse("/", status_code=status.HTTP_302_FOUND)

    


@app.post("/updateUserTweet", response_class=RedirectResponse)
async def updateUserTweet(request: Request):
    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)
    form = await request.form()
    tweet_id = form["tweetId"]  
    content = form["content"]
    tweetImage = form["tweetImage"]
    if user_token:
        storage_client = storage.Client(project=local_constants.PROJECT_NAME)
        bucket = storage_client.bucket(local_constants.PROJECT_STORAGE_BUCKET)
        if tweetImage and tweetImage.filename:
        
            print(form.get("tweetImage"),"364987877777777777")

            addFile(form.get("tweetImage"))

            filename = form.get("tweetImage").filename 
            matchingUrl = None

            print("filenameeeeeeeeeeeeeeeeeeeeee",filename)
            imageUrls = []
            blobs = blobList(None)
            for blob in blobs:
                url = f"https://storage.googleapis.com/{local_constants.PROJECT_STORAGE_BUCKET}/{blob.name}"
                print(url)
                imageUrls.append(url)

            print(imageUrls,"cccccccccccccccccccc")
        

            for url in imageUrls:
                if filename in url:
                    matchingUrl = url
                    break   
        else:
            matchingUrl = None


        try:    
            firestore_db.collection("Tweet").document( tweet_id).update({"tweetContent": content,"imageUrl": matchingUrl})

            user_doc_ref = firestore_db.collection("User").document(user_token["user_id"])
            user_doc = user_doc_ref.get()

            if user_doc.exists:
                user_data = user_doc.to_dict()
                current_tweets = user_data.get("tweets", [])

                for tweet in current_tweets:
                    if tweet["tweetId"] == tweet_id:
                        tweet["tweetContent"] = content
                        tweet["imageUrl"] = matchingUrl

                        break

                user_doc_ref.update({"tweets": current_tweets})

            UserName = await get_username(user_token.get("user_id"))
            current_tweets = await getUserTweetsByFollowing(user_token['user_id']) 
            return templates.TemplateResponse('main.html', {'request': request, 'user_token': user_token, 'error_message': None,'UserName': UserName,"AllTweets":current_tweets})
        except Exception as e:
            return RedirectResponse("/", status_code=status.HTTP_302_FOUND)
    else:
        print("User token is invalid")
        return RedirectResponse("/", status_code=status.HTTP_302_FOUND)


def addDirectory(directory_name):
    storage_client = storage.Client(project=local_constants.PROJECT_NAME)
    bucket = storage_client.bucket(local_constants.PROJECT_STORAGE_BUCKET)

    blob = bucket.blob(directory_name)
    blob.upload_from_string('',content_type="application/x-www-form-urlencoded;charset=UTF-8")

def addFile(file):
    storage_client = storage.Client(project=local_constants.PROJECT_NAME)
    bucket = storage_client.bucket(local_constants.PROJECT_STORAGE_BUCKET)


    print(file.filename,bucket,"img")
    blob = storage.Blob(file.filename,bucket)
    blob.upload_from_file(file.file)

def blobList(prefix):
    storage_client = storage.Client(project=local_constants.PROJECT_NAME)

    return storage_client.list_blobs(local_constants.PROJECT_STORAGE_BUCKET,prefix=prefix)


@app.get("/Profile", response_class=HTMLResponse)
async def Profile(request: Request):
    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)

    if user_token:
        userdata = getTweetsByUserId(user_token["user_id"])
        return templates.TemplateResponse('Profile.html', {'request': request, 'user_token': user_token, 'error_message': None,"userdata":userdata})
    else:
        return templates.TemplateResponse('main.html', {'request': request, 'user_token': None, 'error_message': None})