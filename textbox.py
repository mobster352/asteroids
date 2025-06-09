import pygame
import pygame_textinput

class Textbox():
    def __init__(self, label, screen_width, screen_height, screen_width_divisor, screen_height_divisor):
        self.label = label
        self.screen_size = (screen_width, screen_height)
        self.screen_divior = (screen_width_divisor, screen_height_divisor)
        self.border_rect = None

    def update_textbox(self, screen_width, screen_height):
        self.screen_size = (screen_width, screen_height)

    def draw_textbox(self, font_color, border_color, font, screen):
        textbox_surface, rect = font.render(self.label, font_color)

        rect_width_center = rect[2] / 2
        rect_height_center = rect[3] / 2
        dest = (self.screen_size[0] / self.screen_divior[0] - rect_width_center, self.screen_size[1] / self.screen_divior[1] - rect_height_center)

        margin = 50
        self.border_rect = pygame.Rect(dest[0] - (margin * 2), dest[1] + margin/1.5, rect[2] + (margin * 4), rect[3])
        border_surface = pygame.Surface((self.border_rect[2], self.border_rect[3]))
        pygame.Surface.fill(border_surface, color=border_color)
        screen.blit(border_surface, self.border_rect)

        screen.blit(textbox_surface, dest)

        # return position of rect
        return dest[0] - (margin * 2), dest[1] + margin/1.5

    def check_collisions(self, click_pos):
        border_top_left_point = (self.border_rect[0], self.border_rect[1])
        border_bottom_right_point = (self.border_rect[0] + self.border_rect[2], self.border_rect[1] + self.border_rect[3])

        return (
            # checking left x position
            click_pos[0] >= border_top_left_point[0]
            # checking right x position
            and click_pos[0] <= border_bottom_right_point[0]
            # checking top y position
            and click_pos[1] >= border_top_left_point[1]
            # checking bottom y position
            and click_pos[1] <= border_bottom_right_point[1]
        )