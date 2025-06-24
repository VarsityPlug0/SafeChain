# SafeChain AI

Welcome to SafeChain AI, a sophisticated Django-powered investment platform that leverages AI-driven strategies to help you grow your crypto assets.

## Features

- **User Authentication**: Secure registration and login system with email verification.
- **Investment Tiers**: Multiple investment tiers with varying returns and durations.
- **Wallet System**: Personal wallets for each user to manage deposits, withdrawals, and earnings.
- **Referral Program**: A referral system that rewards users for inviting new members.
- **Admin Dashboard**: A comprehensive admin dashboard for managing users, investments, and platform settings.

## Getting Started

Follow these instructions to get a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

- Python 3.8+
- Pip
- Virtualenv

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/safechain-ai.git
    cd safechain-ai
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3.  **Install the dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up the database:**
    ```bash
    python manage.py migrate
    ```

5.  **Run the development server:**
    ```bash
    python manage.py runserver
    ```

The application will be available at `http://127.0.0.1:8000`.

## Usage

- **Register a new account** or log in with an existing one.
- **Deposit funds** into your wallet to start investing.
- **Choose an investment tier** and make your first investment.
- **Track your earnings** and referrals on your dashboard.
- **Withdraw your profits** to your bank account.

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change. 