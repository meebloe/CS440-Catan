using Microsoft.Xna.Framework;
using Microsoft.Xna.Framework.Graphics;
using Microsoft.Xna.Framework.Input;
using CatanGameLib;
using System.Collections.Generic;
using System.Linq;
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
        private Dictionary<string, Color> _resourceColors;
        private SpriteFont _dynamicFont;
        private List<Tuple<Vector2, string, Color>> _hexNumbers;
        private GameController _catanGame = new GameController();
        private Dictionary<string, Texture2D> _harborIcons;

        private Dictionary<int, Vector2> _hardcodedPositions = new Dictionary<int, Vector2>
        {
            { 0, new Vector2(226.79492f, 87.5f) },
            { 1, new Vector2(270.0962f, 62.5f) },
            { 2, new Vector2(313.39746f, 87.5f) },
            { 3, new Vector2(356.69873f, 62.5f) },
            { 4, new Vector2(400, 87.5f) },
            { 5, new Vector2(443.30127f, 62.5f) },
            { 6, new Vector2(486.60254f, 87.5f) },
            { 7, new Vector2(486.60254f, 137.50002f) },
            { 8, new Vector2(529.9038f, 162.5f) },
            { 9, new Vector2(529.9038f, 212.5f) },
            { 10, new Vector2(573.2051f, 237.5f) },
            { 11, new Vector2(573.2051f, 287.5f) },
            { 12, new Vector2(529.9038f, 312.5f) },
            { 13, new Vector2(529.9038f, 362.5f) },
            { 14, new Vector2(486.60254f, 387.5f) },
            { 15, new Vector2(486.60254f, 437.5f) },
            { 16, new Vector2(443.30127f, 462.5f) },
            { 17, new Vector2(400f, 437.5f) },
            { 18, new Vector2(356.69873f, 462.5f) },
            { 19, new Vector2(313.39746f, 437.5f) },
            { 20, new Vector2(270.0962f, 462.5f) },
            { 21, new Vector2(226.79492f, 437.5f) },
            { 22, new Vector2(226.79492f, 387.5f) },
            { 23, new Vector2(183.49365f, 362.5f) },
            { 24, new Vector2(183.49365f, 312.5f) },
            { 25, new Vector2(140.19238f, 287.5f) },
            { 26, new Vector2(140.19238f, 237.5f) },
            { 27, new Vector2(183.49365f, 212.5f) },
            { 28, new Vector2(183.49365f, 162.5f) },
            { 29, new Vector2(226.79492f, 137.50002f) },
            { 30, new Vector2(270.0962f, 162.5f) },
            { 31, new Vector2(313.39746f, 137.50002f) },
            { 32, new Vector2(356.69873f, 162.5f) },
            { 33, new Vector2(400f, 137.50002f) },
            { 34, new Vector2(443.30127f, 162.5f) },
            { 35, new Vector2(443.30127f, 212.5f) },
            { 36, new Vector2(486.60254f, 237.5f) },
            { 37, new Vector2(486.60254f, 287.5f) },
            { 38, new Vector2(443.30127f, 312.5f) },
            { 39, new Vector2(443.30127f, 362.5f) },
            { 40, new Vector2(400f, 387.5f) },
            { 41, new Vector2(356.69873f, 362.5f) },
            { 42, new Vector2(313.39746f, 387.5f) },
            { 43, new Vector2(270.0962f, 362.5f) },
            { 44, new Vector2(270.0962f, 312.5f) },
            { 45, new Vector2(226.79492f, 287.5f) },
            { 46, new Vector2(226.79492f, 237.5f) },
            { 47, new Vector2(270.0962f, 212.5f) },
            { 48, new Vector2(313.39746f, 237.5f) },
            { 49, new Vector2(356.69873f, 212.5f) },
            { 50, new Vector2(400f, 237.5f) },
            { 51, new Vector2(400f, 287.5f) },
            { 52, new Vector2(356.69873f, 312.5f) },
            { 53, new Vector2(313.39746f, 287.5f) },
        };

        private Dictionary<int, int[]> _harborConnections = new Dictionary<int, int[]>
        {
            { 0, new[] { 0, 1 } }, { 1, new[] { 1, 2 } }, { 2, new[] { 2, 3 } },
            { 3, new[] { 3, 4 } }, { 4, new[] { 4, 5 } }, { 5, new[] { 5, 6 } },
            { 6, new[] { 6, 7 } }, { 7, new[] { 7, 8 } }, { 8, new[] { 8, 9 } },
            { 9, new[] { 9, 10 } }, { 10, new[] { 10, 11 } }, { 11, new[] { 11, 12 } },
            { 12, new[] { 12, 13 } }, { 13, new[] { 13, 14 } }, { 14, new[] { 14, 15 } },
            { 15, new[] { 15, 16 } }, { 16, new[] { 16, 17 } }, { 17, new[] { 17, 18 } },
            { 18, new[] { 18, 19 } }, { 19, new[] { 19, 20 } }, { 20, new[] { 20, 21 } },
            { 21, new[] { 21, 22 } }, { 22, new[] { 22, 23 } }, { 23, new[] { 23, 24 } },
            { 24, new[] { 24, 25 } }, { 25, new[] { 25, 26 } }, { 26, new[] { 26, 27 } },
            { 27, new[] { 27, 28 } }, { 28, new[] { 28, 29 } }, { 29, new[] { 29, 0 } },
        };


        public Game1()
        {
            _graphics = new GraphicsDeviceManager(this);
            Content.RootDirectory = "Content";
            IsMouseVisible = true;
        }

        private void LogDebug(string message)
        {
            File.AppendAllText("debug_log.txt", message + "\n");
        }

        protected override void Initialize()
        {
            // Set window size and apply settings
            _graphics.PreferredBackBufferWidth = 800;
            _graphics.PreferredBackBufferHeight = 600;
            _graphics.ApplyChanges();

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

            _hexNumbers = new List<Tuple<Vector2, string, Color>>();

            base.Initialize();
        }

        protected override void LoadContent()
        {
            _spriteBatch = new SpriteBatch(GraphicsDevice);
            _basicEffect = new BasicEffect(GraphicsDevice)
            {
                VertexColorEnabled = true,
                Projection = Matrix.CreateOrthographicOffCenter(
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

            // Load harbor icons
            _harborIcons = new Dictionary<string, Texture2D>();
            string[] harborTypes = { "brick", "wood", "wheat", "sheep", "stone", "special" };

            foreach (var type in harborTypes)
            {
                string path = $"Content/img/{type}.png";
                if (File.Exists(path))
                {
                    using (FileStream fileStream = new FileStream(path, FileMode.Open))
                    {
                        _harborIcons[type] = Texture2D.FromStream(GraphicsDevice, fileStream);
                    }
                }
                else
                {
                    Console.WriteLine($"Warning: Harbor icon not found for '{type}'.");
                }
            }
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

            Vector2 centerHexPosition = Vector2.Zero;

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
                    List<Hex> _tempBoard = _catanGame.GetHexes();
                    if (hexIndex >= _tempBoard.Count)
                        break;

                    Hex hex = _tempBoard[hexIndex];
                    float x = startX + offsetX + col * hexWidth;
                    float y = startY + row * verticalSpacing;

                    if (hexIndex == 9)  
                    {
                        centerHexPosition = new Vector2(x, y);
                    }

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


            // Draw Harbors and Connections Simultaneously
            foreach (var harbor in _catanGame.GetHarbors())
            {
                // Get the harbor's position
                Vector2 harborPosition = GetHarborPosition(harbor.Position, centerHexPosition, hexWidth, hexHeight);
                Rectangle harborRect = GetHarborRectangle(harborPosition);

                // Draw connection lines first (so they are underneath everything)
                if (_harborConnections.TryGetValue(harbor.Position, out var intersections))
                {
                    foreach (var intersectionIndex in intersections)
                    {
                        if (_hardcodedPositions.TryGetValue(intersectionIndex, out var intersectionPosition))
                        {
                            _drawBatch.DrawLine(new Pen(Color.Black, 3f), harborPosition, intersectionPosition);
                        }
                    }
                }

                // Draw harbor background
                _drawBatch.FillRectangle(new SolidColorBrush(Color.White), harborRect);
                _drawBatch.DrawRectangle(new Pen(Color.Black, 2f), harborRect);
            }

            _drawBatch.End();

            _spriteBatch.Begin();

            foreach (var hexNumber in _hexNumbers)
            {
                Vector2 circleCenter = hexNumber.Item1;
                string numberText = hexNumber.Item2;
                Color textColor = hexNumber.Item3;

                Vector2 textSize = _dynamicFont.MeasureString(numberText);
                Vector2 textPosition = new Vector2(circleCenter.X - textSize.X / 2, circleCenter.Y - textSize.Y / 2 + 4);

                _spriteBatch.DrawString(_dynamicFont, numberText, textPosition, textColor);
            }

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

            /*
            // Draw numbers at their predefined positions
            foreach (var entry in _hardcodedPositions)
            {
                int id = entry.Key;
                Vector2 position = entry.Value;

                Vector2 textSize = _dynamicFont.MeasureString(id.ToString());
                Vector2 textPosition = new Vector2(position.X - textSize.X / 2, position.Y - textSize.Y / 2);

                _spriteBatch.DrawString(_dynamicFont, id.ToString(), textPosition, Color.Black);
            }
            */

            foreach (var harbor in _catanGame.GetHarbors())
            {
                Vector2 harborPosition = GetHarborPosition(harbor.Position, centerHexPosition, hexWidth, hexHeight);

                // Fix: Use `ResourceType` instead of `Type`
                string harborType = harbor.ResourceType.ToLower();

                if (_harborIcons.TryGetValue(harborType, out Texture2D icon))
                {
                    _spriteBatch.Draw(icon, new Rectangle(
                        (int)harborPosition.X - 15, 
                        (int)harborPosition.Y - 15, 
                        30, 30), Color.White);
                }
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

        private Vector2 GetHarborPosition(int position, Vector2 centerHexPosition, float hexWidth, float hexHeight)
        {
            // Base unit adjustments
            float oneHexX = hexWidth; 
            float halfHexX = hexWidth / 2.0f;
            float quarterHexX = hexWidth / 4.0f;
            float oneHexY = hexHeight;
            float halfHexY = hexHeight / 2.0f;
            float quarterHexY = hexHeight / 4.0f;

            // Flat harbors (fixed placements)
            switch (position)
            {
                case 0: return new Vector2(centerHexPosition.X - (1.5f * oneHexX), centerHexPosition.Y - (2.0f * oneHexY) - quarterHexY);
                case 5: return new Vector2(centerHexPosition.X + (1.5f * oneHexX), centerHexPosition.Y - (2.0f * oneHexY) - quarterHexY);
                case 10: return new Vector2(centerHexPosition.X + (3.0f * oneHexX), centerHexPosition.Y);
                case 15: return new Vector2(centerHexPosition.X + (1.5f * oneHexX), centerHexPosition.Y + (2.0f * oneHexY) + quarterHexY);
                case 20: return new Vector2(centerHexPosition.X - (1.5f * oneHexX), centerHexPosition.Y + (2.0f * oneHexY) + quarterHexY);
                case 25: return new Vector2(centerHexPosition.X - (3.0f * oneHexX), centerHexPosition.Y);
            }

            // Grouped indents based on symmetrical inversions

            // Group 1 (Original + X Inverted + Y Inverted + X/Y Inverted)
            if (position == 1 || position == 2) return new Vector2(centerHexPosition.X - halfHexX, centerHexPosition.Y - (2.0f * oneHexY) - quarterHexY);
            if (position == 18 || position == 19) return new Vector2(centerHexPosition.X - halfHexX, centerHexPosition.Y + (2.0f * oneHexY) + quarterHexY);
            if (position == 3 || position == 4) return new Vector2(centerHexPosition.X + halfHexX, centerHexPosition.Y - (2.0f * oneHexY) - quarterHexY);
            if (position == 16 || position == 17) return new Vector2(centerHexPosition.X + halfHexX, centerHexPosition.Y + (2.0f * oneHexY) + quarterHexY);

            // Group 2 (Original + Inversions)
            if (position == 6 || position == 7) return new Vector2(centerHexPosition.X + (1.5f * oneHexX) + halfHexX, centerHexPosition.Y - (2.0f * oneHexY) - quarterHexY + halfHexY + quarterHexY);
            if (position == 13 || position == 14) return new Vector2(centerHexPosition.X + (1.5f * oneHexX) + halfHexX, centerHexPosition.Y + (2.0f * oneHexY) + quarterHexY - halfHexY - quarterHexY);
            if (position == 21 || position == 22) return new Vector2(centerHexPosition.X - (1.5f * oneHexX) - halfHexX, centerHexPosition.Y + (2.0f * oneHexY) + quarterHexY - halfHexY - quarterHexY);
            if (position == 28 || position == 29) return new Vector2(centerHexPosition.X - (1.5f * oneHexX) - halfHexX, centerHexPosition.Y - (2.0f * oneHexY) - quarterHexY + halfHexY + quarterHexY);

            // Group 3 (Original + Inversions)
            if (position == 8 || position == 9) return new Vector2(centerHexPosition.X + (3.0f * oneHexX) - (2.0f * quarterHexX), centerHexPosition.Y - halfHexY - quarterHexY);
            if (position == 11 || position == 12) return new Vector2(centerHexPosition.X + (3.0f * oneHexX) - (2.0f * quarterHexX), centerHexPosition.Y + halfHexY + quarterHexY);
            if (position == 23 || position == 24) return new Vector2(centerHexPosition.X - (3.0f * oneHexX) + (2.0f * quarterHexX), centerHexPosition.Y + halfHexY + quarterHexY);
            if (position == 26 || position == 27) return new Vector2(centerHexPosition.X - (3.0f * oneHexX) + (2.0f * quarterHexX), centerHexPosition.Y - halfHexY - quarterHexY);

            // Default return in case of errors
            return centerHexPosition;
        }

        private Rectangle GetHarborRectangle(Vector2 position)
        {
            int size = 40;
            return new Rectangle(
                (int)Math.Round(position.X - size / 2), 
                (int)Math.Round(position.Y - size / 2), 
                size - 5, 
                size + 5
            );
        }
    }
}
