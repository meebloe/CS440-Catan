# CS440-Catan

This project uses Tensorflow to implement Deep Reinforcement Learning and build an AI that plays Catan. The Catan game used to train the AI is made with MonoGame which is a .NET framework that builds simple 2D games.

## Installation

MonoGame requires the .NET SDK. Download and install the latest version from: [Download .NET SDK](https://dotnet.microsoft.com/en-us/download/dotnet)

Verify .NET installation:

```dotnet --version```

Install MonoGame:

```dotnet new --install MonoGame.Templates.CSharp```

## Setup and Run the Game

Navigate to game folder:

```cd CatanGame```

Install Packages:

```dotnet restore```

To compile the game, run:

```dotnet build```

To launch the game, use:

```dotnet run```
