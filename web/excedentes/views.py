from django.shortcuts import render
import excedentes.models

# Create your views here.
def dash_board(request):
    return render(request, 'excedentes/dash_board.html', {})