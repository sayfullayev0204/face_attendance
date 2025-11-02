Django e-learning project (sequential videos + tests)
Run:
  python -m venv venv
  source venv/bin/activate   (Windows: venv\Scripts\activate)
  pip install -r requirements.txt
  python manage.py migrate
  python manage.py createsuperuser
  python manage.py runserver

Notes:
- Upload video files via admin (Video.video_file).
- Media files served in DEBUG mode by Django.
- First video of a lesson is always unlocked. Next ones unlock after previous viewed fully (client sends POST on video 'ended').
- Test opens only after all videos watched.
