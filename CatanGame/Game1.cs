using Microsoft.Xna.Framework;
using Microsoft.Xna.Framework.Graphics;
using Microsoft.Xna.Framework.Input;
using CatanGameLib;
using System.Collections.Generic;
using System;

namespace CatanGame
{
    public class Game1 : Game
    {
        private GraphicsDeviceManager _graphics;
        private SpriteBatch _spriteBatch;
        private BasicEffect _basicEffect;
        private Board _board;
        private Dictionary<string, Color> _resourceColors;

        public Game1()
        {
            _graphics = new GraphicsDeviceManager(this);
            Content.RootDirectory = "Content";
            IsMouseVisible = true;
        }

        protected override void Initialize()
        {
            // Set window size
            _graphics.PreferredBackBufferWidth = 800;
            _graphics.PreferredBackBufferHeight = 600;
            _graphics.ApplyChanges();

            // Generate the board
            _board = BoardGenerator.GenerateBoard();

            // Print hex information for debugging
            Console.WriteLine("Board initialized with the following hexes:");
            foreach (var hex in _board.Hexes)
            {
                Console.WriteLine($"Hex ID: {hex.Id}, Resource: {hex.Resource}, Number: {(hex.Number.HasValue ? hex.Number.Value.ToString() : "None")}");
            }

            // Define colors for resources
            _resourceColors = new Dictionary<string, Color>
            {
                { "Wood", Color.ForestGreen },
                { "Brick", Color.Brown },
                { "Sheep", Color.LightGreen },
                { "Wheat", Color.Yellow },
                { "Stone", Color.Gray },
                { "Desert", Color.SandyBrown }
            };

            base.Initialize();
        }

        protected override void LoadContent()
        {
            _spriteBatch = new SpriteBatch(GraphicsDevice);
            _basicEffect = new BasicEffect(GraphicsDevice)
            {
                VertexColorEnabled = true,
                Projection = Matrix.CreateOrthographicOffCenter
                (
                    0, GraphicsDevice.Viewport.Width,
                    GraphicsDevice.Viewport.Height, 0,
                    0, 1
                )
            };
        }

        protected override void Update(GameTime gameTime)
        {
            if (Keyboard.GetState().IsKeyDown(Keys.Escape))
                Exit();

            base.Update(gameTime);
        }

        protected override void Draw(GameTime gameTime)
        {
            GraphicsDevice.Clear(Color.CornflowerBlue);

            float hexRadius = 50f;
            float hexWidth = (float)(Math.Sqrt(3) * hexRadius);
            float hexHeight = 2f * hexRadius;
            float verticalSpacing = 0.75f * hexHeight;

            // Define the number of hexagons in each row
            int[] rowHexCounts = { 3, 4, 5, 4, 3 };

            // Calculate starting position to center the grid
            float startX = (_graphics.PreferredBackBufferWidth - (5 * hexWidth)) / 2;
            float startY = (_graphics.PreferredBackBufferHeight - (5 * verticalSpacing)) / 2;

            int hexIndex = 0;

            for (int row = 0; row < rowHexCounts.Length; row++)
            {
                int hexCount = rowHexCounts[row];

                float offsetX = (row == 0 || row == 4) ? hexWidth * 1f :
                                (row % 2 == 1) ? hexWidth * 0.5f : 0;

                for (int col = 0; col < hexCount; col++)
                {
                    if (hexIndex >= _board.Hexes.Count)
                        break;

                    Hex hex = _board.Hexes[hexIndex];
                    float x = startX + offsetX + col * hexWidth;
                    float y = startY + row * verticalSpacing;

                    // Determine the color based on the resource type
                    Color hexColor = _resourceColors.ContainsKey(hex.Resource) ? _resourceColors[hex.Resource] : Color.Magenta;

                    DrawFilledHexagon(new Vector2(x, y), hexRadius, hexColor);

                    hexIndex++;
                }
            }

            base.Draw(gameTime);
        }

        private void DrawHexOutline(Vector2 center, float radius, Color borderColor)
        {
            VertexPositionColor[] outlineVertices = new VertexPositionColor[7];

            for (int i = 0; i < 6; i++)
            {
                float angle = MathHelper.ToRadians(60 * i - 30);
                Vector2 position = new Vector2(
                    center.X + radius * (float)Math.Cos(angle),
                    center.Y + radius * (float)Math.Sin(angle)
                );
                outlineVertices[i] = new VertexPositionColor(new Vector3(position, 0), borderColor);
            }

            // Close the hexagon by connecting the last vertex to the first
            outlineVertices[6] = outlineVertices[0];

            foreach (var pass in _basicEffect.CurrentTechnique.Passes)
            {
                pass.Apply();

                GraphicsDevice.DrawUserPrimitives(
                    PrimitiveType.LineStrip,
                    outlineVertices, 0, 6
                );
            }
        }

        private void DrawFilledHexagon(Vector2 center, float radius, Color fillColor)
        {
            VertexPositionColor[] vertices = new VertexPositionColor[6];
            for (int i = 0; i < 6; i++)
            {
                float angle = MathHelper.ToRadians(60 * i - 30);
                Vector2 position = new Vector2(
                    center.X + radius * (float)Math.Cos(angle),
                    center.Y + radius * (float)Math.Sin(angle)
                );
                vertices[i] = new VertexPositionColor(new Vector3(position, 0), fillColor);
            }

            short[] indices = new short[]
            {
                0, 1, 2,
                0, 2, 3,
                0, 3, 4,
                0, 4, 5,
                0, 5, 0
            };

            // Draw filled hexagon
            foreach (var pass in _basicEffect.CurrentTechnique.Passes)
            {
                pass.Apply();

                GraphicsDevice.DrawUserIndexedPrimitives(
                    PrimitiveType.TriangleList,
                    vertices, 0, 6,
                    indices, 0, 4
                );
            }

            // Draw hexagon outline (black border)
            DrawHexOutline(center, radius, Color.Black);
        }
    }
}
