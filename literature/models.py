from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.urls import reverse
from django.core.validators import MinLengthValidator

class Genre(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

class Author(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='author_profile')
    bio = models.TextField()
    birth_date = models.DateField(null=True, blank=True)
    photo = models.ImageField(upload_to='authors/', blank=True)

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name}"

class Book(models.Model):
    title = models.CharField(max_length=200)
    author = models.ForeignKey(Author, on_delete=models.CASCADE, related_name='books')
    genre = models.ForeignKey(Genre, on_delete=models.SET_NULL, null=True, related_name='books')
    published_date = models.DateField()
    description = models.TextField()
    cover = models.ImageField(upload_to='book_covers/', blank=True)

    def __str__(self):
        return f"{self.title} ({self.published_date.year})"

    def get_absolute_url(self):
        return reverse('literature:book_detail', kwargs={'pk': self.pk})

class Post(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DF', 'Draft'
        PUBLISHED = 'PB', 'Published'
        ARCHIVED = 'AR', 'Archived'

    title = models.CharField(max_length=250)
    slug = models.SlugField(max_length=250, unique_for_date='publish')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blog_posts')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='posts')
    body = models.TextField(validators=[MinLengthValidator(10)])
    publish = models.DateTimeField(default=timezone.now)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=2, choices=Status.choices, default=Status.DRAFT)

    class Meta:
        ordering = ['-publish']
        indexes = [models.Index(fields=['-publish']),]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('post_detail', kwargs={
            'pk': self.pk,
            'slug': self.slug
        })

class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    body = models.TextField()
    created = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ['created']
        indexes = [models.Index(fields=['created']),]

    def __str__(self):
        return f'Comment by {self.author.username} on {self.post}'
    def get_similar_posts(self):
        return Post.objects.filter(
            book__genre=self.book.genre
        ).exclude(pk=self.pk)[:5]
    
    def get_absolute_url(self):
        return reverse('literature:post_detail', kwargs={'pk': self.pk})