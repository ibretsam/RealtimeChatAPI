# Realtime Chat Application

This repository contains the source code for a Realtime Chat Application. The application is built using Django, Channels, and JWT for authentication.
Check out the repository for the Application (built using React Native) here: https://github.com/ibretsam/RealtimeChatApp

## Features

- Real-time messaging: Users can send and receive messages in real time.
- Authentication: The application uses JWT for user authentication.
- Pagination: Messages are paginated to improve performance and user experience.

## Project Structure

The main components of the project are:

- `consumers.py`: This file contains the main logic for handling WebSocket connections, receiving and sending messages.
- `models.py`: This file defines the data models for the application, including `User`, `Connection`, and `Message`.
- `serializers.py`: This file contains serializers for converting model instances to JSON format and vice versa.
- `utils.py`: This file contains utility functions used throughout the application.

## How to Run

1. Clone the repository.
2. Install the dependencies using pip: `pip install -r requirements.txt`.
3. Run the Django server: `python manage.py runserver`.

## Contributing

Contributions are welcome! Please read the contributing guidelines before starting.

## License

This project is licensed under the terms of the MIT license.