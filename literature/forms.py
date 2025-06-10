from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Post, Comment, Book, Author, Genre
from django.utils import timezone

def is_author(user):
    """Проверяет, является ли пользователь автором"""
    return hasattr(user, 'author_profile') and user.author_profile is not None

class UserRegisterForm(UserCreationForm):
    email = forms.EmailField()
    first_name = forms.CharField(max_length=100)
    last_name = forms.CharField(max_length=100)

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']

    """def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Пользователь с таким email уже существует.")
        return email"""

class UserEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].required = True

class AuthorProfileForm(forms.ModelForm):
    birth_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=False
    )

    class Meta:
        model = Author
        fields = ['bio', 'birth_date', 'photo']

class BookForm(forms.ModelForm):
    class Meta:
        model = Book
        fields = ['title', 'genre', 'description', 'cover']
        
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super(BookForm, self).__init__(*args, **kwargs)
    
    def clean(self):
        cleaned_data = super().clean()
        # Автоматически добавляем автора
        if self.user and hasattr(self.user, 'author_profile'):
            cleaned_data['author'] = self.user.author_profile
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Устанавливаем автора
        if self.user and hasattr(self.user, 'author_profile'):
            instance.author = self.user.author_profile
        
        # Устанавливаем текущую дату публикации
        instance.published_date = timezone.now().date()
        
        if commit:
            instance.save()
        return instance

class PostForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(PostForm, self).__init__(*args, **kwargs)
        self.fields['title'].initial = ''
        # Если пользователь - автор, фильтруем книги только его авторства
        if user and is_author(user):
            self.fields['book'].queryset = Book.objects.filter(author=user.author_profile)
        # Для суперпользователя показываем все книги
        elif user and user.is_superuser:
            self.fields['book'].queryset = Book.objects.all()
        # Для обычных пользователей не показываем книги (но они не должны создавать посты)
        else:
            self.fields['book'].queryset = Book.objects.none()

    class Meta:
        model = Post
        fields = ['title', 'book', 'body', 'status']


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['body']

class GenreForm(forms.ModelForm):
    class Meta:
        model = Genre
        fields = ['name', 'description']