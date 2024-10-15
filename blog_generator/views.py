import json
import os
from typing import Optional, Dict, Any
import assemblyai as aai
import openai
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpRequest, HttpResponse
from pytubefix import YouTube
from django.conf import settings
from .models import BlogPost

# Create your views here.

@login_required
def index(request: HttpRequest) -> HttpResponse:
    return render(request, 'index.html')

@csrf_exempt
def generate_blog(request: HttpRequest) -> JsonResponse:
    if request.method == 'POST':
        try:
            data: Dict[str, Any] = json.loads(request.body)
            yt_link: str = data['link']

        except (KeyError, json.JSONDecodeError):
            return JsonResponse({'error': 'Invalid data sent'}, status=400)
        
        # get yt title
        title: str = yt_title(yt_link)

        # get transcript
        transcription: Optional[str] = get_transcription(yt_link)
        if not transcription:
            return JsonResponse({'error': 'Failed to get transcript'}, status=500)

        # mock blog generation
        blog_content: str = transcription[:500] + "..."
        
        # save blog article to database
        new_blog_article = BlogPost.objects.create(
            user=request.user,
            youtube_title=title,
            youtube_link=yt_link,
            generated_content=blog_content
        )
        new_blog_article.save()

        # return blog article as a response
        return JsonResponse({'content': blog_content})
      
    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)
  
def yt_title(link: str) -> str:
    yt = YouTube(link)
    title: str = yt.title
    return title

def download_audio(link: str) -> str:
    yt = YouTube(link)
    video = yt.streams.filter(only_audio=True).first()
    out_file: str = video.download(output_path=settings.MEDIA_ROOT)
    base, ext = os.path.splitext(out_file)
    new_file: str = base + '.mp3'
    os.rename(out_file, new_file)
    return new_file

def get_transcription(link: str) -> Optional[str]:
    audio_file: str = download_audio(link)
    aai.settings.api_key = 'XXX'

    config = aai.TranscriptionConfig(speech_model=aai.SpeechModel.nano, language_code="cs")

    transcriber = aai.Transcriber(config=config)
    transcript = transcriber.transcribe(audio_file)
  
    return transcript.text if transcript else None

def generate_blog_from_transcription(transcription: str) -> str:
    openai.api_key = "XXX"

    prompt: str = f"Based on the following transcript from a YouTube video, write a comprehensive blog article...\n\n{transcription}\n\nArticle:"

    response = openai.Completion.create(
        model="gpt-3.5-turbo-instruct",
        prompt=prompt,
        max_tokens=1000
    )

    generated_content: str = response.choices[0].text.strip()
    return generated_content

def blog_list(request: HttpRequest) -> HttpResponse:
    blog_articles = BlogPost.objects.filter(user=request.user)
    return render(request, "all-blogs.html", {'blog_articles': blog_articles})

def blog_details(request: HttpRequest, pk: int) -> HttpResponse:
    blog_article_detail = BlogPost.objects.get(id=pk)
    if request.user == blog_article_detail.user:
        return render(request, 'blog-details.html', {'blog_article_detail': blog_article_detail})
    else:
        return redirect('/')

def user_login(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        username: str = request.POST['username']
        password: str = request.POST['password']

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('/')
        else:
            error_message: str = 'Invalid username or password'
            return render(request, 'login.html', {'error_message': error_message})

    return render(request, 'login.html')

def user_signup(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        username: str = request.POST['username']
        email: str = request.POST['email']
        password: str = request.POST['password']
        repeat_password: str = request.POST['repeatPassword']

        if password == repeat_password:
            try:
                user = User.objects.create_user(username, email, password)
                user.save()
                login(request, user)
                return redirect('/')
            except:
                error_message: str = 'Error creating the account'
                return render(request, 'signup.html', {'error_message': error_message})

        else:
            error_message: str = 'Password do not match'
            return render(request, 'signup.html', {'error_message': error_message})

    return render(request, 'signup.html')

def user_logout(request: HttpRequest) -> HttpResponse:
    logout(request)
    return redirect('/')
