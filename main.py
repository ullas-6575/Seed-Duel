import pygame

pygame.init()

screen = pygame.display.set_mode((1000, 650))
pygame.display.set_caption("Seed Duel")

running = True

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    screen.fill((240, 245, 250))
    pygame.display.flip()

pygame.quit()
