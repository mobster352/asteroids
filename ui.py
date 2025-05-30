import pygame

class UI:
    def __init__(self, score, high_score):
        self.__score = score
        self.__high_score = high_score

    def get_score(self):
        return self.__score

    def update_score(self, score):
        self.__score += score

    def get_high_score(self):
        return self.__high_score

    def update_high_score(self, score):
        self.__high_score = score