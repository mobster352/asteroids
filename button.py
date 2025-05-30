import pygame

class Button:
    def __init__(self, label, screen_width, screen_height, screen_width_divisor, screen_height_divisor):
        self.label = label
        self.screen_size = (screen_width, screen_height)
        self.screen_divior = (screen_width_divisor, screen_height_divisor)
        self.border_rect = None

    def update_button(self, screen_width, screen_height):
        self.screen_size = (screen_width, screen_height)

    def draw_button(self, font_color, border_color, font, screen):
        button_surface, rect = font.render(self.label, font_color)

        rect_width_center = rect[2] / 2
        rect_height_center = rect[3] / 2
        dest = (self.screen_size[0] / self.screen_divior[0] - rect_width_center, self.screen_size[1] / self.screen_divior[1] - rect_height_center)

        margin = 10
        self.border_rect = pygame.Rect(dest[0] - margin, dest[1] - margin, rect[2] + (margin * 2), rect[3] + (margin * 2))
        border_surface = pygame.Surface((self.border_rect[2], self.border_rect[3]))
        pygame.Surface.fill(border_surface, color=border_color)
        screen.blit(border_surface, self.border_rect)

        screen.blit(button_surface, dest)

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