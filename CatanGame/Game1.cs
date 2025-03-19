using Microsoft.Xna.Framework;
using Microsoft.Xna.Framework.Graphics;
using Microsoft.Xna.Framework.Input;
using CatanGameLib;
using System.Collections.Generic;
using System;
using LilyPath;
using SpriteFontPlus;
using System.IO;

namespace CatanGame
{
    public class Game1 : Game
    {
        private GraphicsDeviceManager _graphics;
        private SpriteBatch _spriteBatch;
        private BasicEffect _basicEffect;
        private DrawBatch _drawBatch;
        private Board _board;
        private Dictionary<string, Color> _resourceColors;
        private SpriteFont _dynamicFont;
        private List<Tuple<Vector2, string, Color>> _hexNumbers; // Stores positions, numbers, and colors for hex numbers

        public Game1()
        {
            _graphics = new GraphicsDeviceManager(this);
            Content.RootDirectory = "Content";
            IsMouseVisible = true;
        }

        protected override void Initialize()
        {
            // Set window size and apply settings
            _graphics.PreferredBackBufferWidth = 800;
            _graphics.PreferredBackBufferHeight = 600;
            _graphics.ApplyChanges();

            // Generate the game board with hex tiles
            _board = BoardGenerator.GenerateBoard();

            // Define colors for different resource types
            _resourceColors = new Dictionary<string, Color>
            {
                { "Wood", Color.ForestGreen },
                { "Brick", Color.Brown },
                { "Sheep", Color.LightGreen },
                { "Wheat", Color.Yellow },
                { "Stone", Color.Gray },
                { "Desert", Color.SandyBrown }
            };

            _hexNumbers = new List<Tuple<Vector2, string, Color>>(); // Holds text data for hex numbers
            base.Initialize();
        }

        protected override void LoadContent()
        {
            // Initialize drawing components
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

            _drawBatch = new DrawBatch(GraphicsDevice);

            // Load font from external file
            string fontPath = "Content/Fonts/ARIAL.TTF";
            if (!File.Exists(fontPath))
            {
                throw new FileNotFoundException($"Font file not found: {fontPath}");
            }

            // Bake the font dynamically for rendering text
            byte[] fontBytes = File.ReadAllBytes(fontPath);
            _dynamicFont = TtfFontBaker.Bake(fontBytes, 30, 1024, 1024, new[] { CharacterRange.BasicLatin })
                .CreateSpriteFont(GraphicsDevice);
        }

        protected override void Update(GameTime gameTime)
        {
            // Exit game if the Escape key is pressed
            if (Keyboard.GetState().IsKeyDown(Keys.Escape))
                Exit();

            base.Update(gameTime);
        }

        protected override void Draw(GameTime gameTime)
        {
            // Clear the screen with a background color
            GraphicsDevice.Clear(Color.CornflowerBlue);

            // Define hexagon size and spacing
            float hexRadius = 50f;
            float hexWidth = (float)(Math.Sqrt(3) * hexRadius);
            float hexHeight = 2f * hexRadius;
            float verticalSpacing = 0.75f * hexHeight;

            int[] rowHexCounts = { 3, 4, 5, 4, 3 }; // Number of hexes per row
            float startX = (_graphics.PreferredBackBufferWidth - (5 * hexWidth)) / 2;
            float startY = (_graphics.PreferredBackBufferHeight - (5 * verticalSpacing)) / 2;

            int hexIndex = 0;
            _hexNumbers.Clear(); // Reset stored hex numbers before drawing

            _drawBatch.Begin(DrawSortMode.Deferred);

            // Loop through each row to position and draw hexes
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

                    // Get the corresponding color for this hex
                    Color hexColor = _resourceColors.ContainsKey(hex.Resource) ? _resourceColors[hex.Resource] : Color.Magenta;
                    DrawFilledHexagon(new Vector2(x, y), hexRadius, hexColor);

                    float circleRadius = 18f;
                    var circleCenter = new Vector2(x, y);

                    // Only draw number circles for non-desert tiles
                    if (hex.Resource != "Desert")
                    {
                        _drawBatch.FillCircle(new SolidColorBrush(Color.White), circleCenter, circleRadius);
                        _drawBatch.DrawCircle(new Pen(Color.Black, 2f), circleCenter, circleRadius);
                    }

                    // Store hex number data if this hex has a number
                    if (hex.Number.HasValue)
                    {
                        string numberText = hex.Number.Value.ToString();
                        Color textColor = (hex.Number == 6 || hex.Number == 8) ? Color.Red : Color.Black;
                        _hexNumbers.Add(new Tuple<Vector2, string, Color>(circleCenter, numberText, textColor));
                    }

                    hexIndex++;
                }
            }

            _drawBatch.End();

            _spriteBatch.Begin();

            // Draw stored hex numbers on top of circles
            foreach (var hexNumber in _hexNumbers)
            {
                Vector2 circleCenter = hexNumber.Item1;
                string numberText = hexNumber.Item2;
                Color textColor = hexNumber.Item3;

                Vector2 textSize = _dynamicFont.MeasureString(numberText);
                Vector2 textPosition = new Vector2(circleCenter.X - textSize.X / 2, circleCenter.Y - textSize.Y / 2 + 4);

                _spriteBatch.DrawString(_dynamicFont, numberText, textPosition, textColor);
            }

            _spriteBatch.End();

            base.Draw(gameTime);
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

            foreach (var pass in _basicEffect.CurrentTechnique.Passes)
            {
                pass.Apply();
                GraphicsDevice.DrawUserIndexedPrimitives(PrimitiveType.TriangleList, vertices, 0, 6, indices, 0, 4);
            }

            DrawHexOutline(center, radius, Color.Black);
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

            outlineVertices[6] = outlineVertices[0];

            foreach (var pass in _basicEffect.CurrentTechnique.Passes)
            {
                pass.Apply();
                GraphicsDevice.DrawUserPrimitives(PrimitiveType.LineStrip, outlineVertices, 0, 6);
            }
        }
    }
}
