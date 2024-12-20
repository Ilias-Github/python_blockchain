# Importing built-in packages
import functools
import hashlib
import collections
import json
import pathlib

# Importing our own code
import hash_util
from block import Block
from transaction import Transaction

MINING_REWARD = 10

blockchain = []
# Transactions need to be processed before adding them to the blockchain
open_transactions = []
owner = 'Ilias'


def load_data():
    file = pathlib.Path('blockchain.json')
    try:
        with open(file, mode='r') as f:
            content = f.readlines()
            global blockchain
            global open_transactions

            blockchain = json.loads(content[0][:-1])
            updated_blockchain = []
            # Convert the retrieved blockchain from the file to an ordered dictionary
            for block in blockchain:
                # Convert each transaction block in the list to a transaction object
                converted_tx = [Transaction(tx['sender'], tx['recipient'], tx['amount']) for tx in
                                block['transactions']]
                # TODO: Clean this up
                updated_block = Block(block['index'], block['previous_hash'], converted_tx, block['proof'],
                                      block['timestamp'])
                updated_block = {
                    'previous_hash': block['previous_hash'],
                    'proof': block['proof'],
                    'transactions': [
                        collections.OrderedDict([
                            ['sender', tx['sender']], ['recipient', tx['recipient']], ['amount', tx['amount']]
                        ]) for tx in block['transactions']]
                }
                updated_blockchain.append(updated_block)
            blockchain = updated_blockchain

            open_transactions = json.loads(content[1])
            converted_transactions = []

            # Retrieve the open transactions and convert them to a transaction object
            for tx in open_transactions:
                updated_transaction = Transaction(tx['sender'], tx['recipient'], tx['amount'])
                converted_transactions.append(updated_transaction)
            open_transactions = converted_transactions
    except (IOError, IndexError):
        # Initialise the blockchain if no data exists
        # The very first block in the blockchain. Used to init the blockchain. No important information is stored. The proof is
        # meaningless

        genesis_block = Block(0, '', [], 100, 0)

        blockchain = [genesis_block]
        open_transactions = []


load_data()


def save_data():
    try:
        with open('blockchain.json', mode='w') as f:
            savable_chain = [block.__dict__ for block in
                             [Block(block_el.index, block_el.previous_hash,
                                    [tx.__dict__ for tx in block_el.transactions], block_el.proof, block_el.timestamp)
                              for
                              block_el in blockchain]]
            f.write(json.dumps(savable_chain))
            f.write('\n')
            # TODO: Play around with the two lines below
            savable_tx = [tx.__dict__ for tx in open_transactions]
            f.write(json.dumps(savable_tx))
    except IOError:
        print('Saving failed!')


def valid_proof(transactions, last_hash, proof):
    # To validate our proof we need to create a string of the arguments. This enables us to calculate a new hash. To do
    # this, we need to convert the transaction objects to an ordered dictionary of transactions.
    guess = (str(tx.to_ordered_dict() for tx in transactions) + last_hash + str(proof)).encode()
    guess_hash = hashlib.sha256(guess).hexdigest()

    # The proof of work is only valid when the hash starts a predefined set of random characters defined by us.
    return guess_hash[0:2] == '00'


def proof_of_work():
    # Calculate the proof of work by incrementing the proof until the requirements of valid_proof are satisfied
    # To do that, we need the last block of the chain, the last block in hashed form and the initial proof (this is a
    # random value we assign to it)
    last_block = blockchain[-1]
    last_hash = hash_util.hash_block(last_block)
    proof = 0

    while not valid_proof(open_transactions, last_hash, proof):
        proof += 1

    return proof


def get_balance(participant):
    """Checks the current balance of the user by adding up the funds sent with the funds still in the open transactions
    subtracting the funds already received"""

    # Check using list comprehension every block in the blockchain for where the given participant is the sender.
    # Take the transaction amount and save that to the list
    tx_sender = [[tx.amount for tx in block.transactions if tx.sender == participant] for block in blockchain]

    # Using list comprehension check every transaction in the open transactions for the given participant. Save up all
    # the amounts where the participant is the sender
    # open_tx_sender = [[tx['amount'] for tx in transaction['transactions'] if tx['sender'] == participant] for transaction in open_transactions]
    open_tx_sender = [tx.amount for tx in open_transactions if tx.sender == participant]

    # Save all the send funds transactions so we can compare them to the funds received later on
    tx_sender.append(open_tx_sender)

    # Calculate the total amount sent by the given participant by using a reduce function.
    # The reduce function is there to reduce the given iterable to a single value
    # In the lambda expression, we define two variables. The first variable is the reduced value (the end result), the
    # second variable is the next element in the iterable we need to process. After the colon is the logic we want to
    # apply to reduce the list. In This case we want to sum up the numbers. Since we're passing a nested list which may
    # contain multiple values, we want to add them up before reducing them.
    #
    # Before executing the operation, we check with a ternary if the value is greater than 0. We do this in cases where
    # there is no value (for example with the Genesis block)
    amount_sent = functools.reduce(lambda tx_sum, tx_amt: tx_sum + sum(tx_amt) if len(tx_amt) > 0 else tx_sum + 0,
                                   tx_sender, 0)

    # Check using list comprehensions all the transactions from the given participant to calculate al the funds received
    tx_recipient = [[tx.amount for tx in block.transactions if tx.recipient == participant] for block in
                    blockchain]

    # Calculate the total amount received by the given participant
    amount_received = functools.reduce(lambda tx_sum, tx_amt: tx_sum + sum(tx_amt) if len(tx_amt) > 0 else tx_sum + 0,
                                       tx_recipient, 0)

    # Calculate the balance of the participant
    return amount_received - amount_sent


def get_last_blockchain_value():
    if len(blockchain) < 1:
        return None
    return blockchain[-1]


def verify_transaction(transaction):
    """Verify if the sender has enough funds by comparing the balance of the sender with the transaction amount"""
    sender_balance = get_balance(transaction.sender)
    tx_amount = transaction.amount

    return sender_balance >= tx_amount


# Adds transaction to the blockchain
def add_transaction(transaction):
    sender = transaction['sender']
    recipient = transaction['recipient']
    amount = transaction['amount']

    # Since dictionaries are unordered, the calculated hash could be calculated wrong because the position of elements
    # in the dictionary aren't set. Ordered dictionary keeps (like the name implies) the dictionary ordered
    # transaction = collections.OrderedDict(
    #     [('sender', sender), ('recipient', recipient), ('amount', amount)]
    # )
    new_transaction = Transaction(sender, recipient, amount)

    if verify_transaction(new_transaction):
        # Dictionary because each key-value pair needs to be unique
        open_transactions.append(collections.OrderedDict([
            ['sender', sender],
            ['recipient', recipient],
            ['amount', amount]
        ]))

        save_data()
        return True

    return False


def mine_block():
    # Get the last block in the chain to save as a hash in the new block
    last_block = blockchain[-1]
    # Hash the block using the predefined hashing function
    hashed_block = hash_util.hash_block(last_block)
    proof = proof_of_work()

    # The miner of the block gets a reward
    reward_transaction = Transaction('MINING', owner, MINING_REWARD)

    # Make a copy of the values in open transactions. By selecting the values, you create a copy of the values, not of
    # the reference.
    # The colon is a range selector that selects the whole list as a range.
    # Note that this only creates a shallow copy meaning that complex data structures (like other lists) aren't copied
    # over but only referenced. So changing the nested list results in the original list being modified
    # We don't want to edit the open transactions in case there is a problem mining since we only want to award users
    # who have actually mined a block
    copied_transactions = open_transactions[:]
    copied_transactions.append(reward_transaction)

    # The new block saves the previous block as a hash
    block = Block(len(blockchain), hashed_block, copied_transactions, proof)

    blockchain.append(block)

    return True


# The recipient and amount is important to know when making a transaction
def get_transaction_value_and_recipient():
    recipient = input('Enter the name of the recipient: ')
    amount = float(input('Enter the amount you want to send: '))
    return {'sender': owner, 'recipient': recipient, 'amount': amount}


# User keyboard input
def get_user_choice():
    user_input = input('Your choice: ')
    return user_input


# Print all the blocks in the chain
def print_blockchain_elements():
    for block in blockchain:
        print('Outputting Block')
        print(block)
    # Else is always executed after the loop is finished
    else:
        print('-' * 20)


# Verify if the blockchain isn't manipulated
def verify_chain():
    # Enumerate adds a counter to an iterable
    for (index, block) in enumerate(blockchain):
        # The first block doesn't have any other block to compare to so skip it
        if index == 0:
            continue
        if block.previous_hash != hash_util.hash_block(blockchain[index - 1]):
            print('prev ' + block.previous_hash)
            print('next ' + hash_util.hash_block(blockchain[index - 1]))
            return False
        if not valid_proof(block.transactions[:-1], block.previous_hash, block.proof):
            print('Proof of work was invalid')
            return False
    return True


def verify_transactions():
    """
        Verifies if all open transactions are valid. Since we aren't able to add invalid transactions, this code might
        be redundant. It's mostly meant to play around with the all() function within python
    """
    # This list comprehension does the same as the code below it, but in a shorter way.
    # We check if all open transactions are valid. If even one is invalid, this method returns False
    return all([verify_transaction(tx) for tx in open_transactions])

    # is_valid = True
    # for tx in open_transactions:
    #     if verify_transaction(tx):
    #         is_valid = True
    #     else:
    #         is_valid = False
    # return is_valid


waiting_for_input = True

while waiting_for_input:
    # Menu for the user to interact with the blockchain
    print('Please choose')
    print('1: Add a new transaction value')
    print('2: Mine a new block')
    print('3: Output the blockchain blocks')
    print('4: Check transaction validity')
    print('q: Quit')

    user_choice = get_user_choice()

    if user_choice == '1':
        transaction = get_transaction_value_and_recipient()
        if add_transaction(transaction):
            print('Added transaction')
        else:
            print('Transaction failed')
        print(open_transactions)
    elif user_choice == '2':
        if mine_block():
            save_data()
            # Set the open transactions to an empty list because they're all processed
            open_transactions = []
    elif user_choice == '3':
        print_blockchain_elements()
    elif user_choice == '4':
        if verify_transactions():
            print('All transactions valid')
        else:
            print('There are invalid transactions')
    elif user_choice == 'q':
        waiting_for_input = False
    else:
        print('Input was invalid, please pick a value from the list!')
        verify_chain()
    if not verify_chain():
        print_blockchain_elements()
        print('Invalid blockchain!')
        break
    print('Balance of {}: {:6.2f}'.format(owner, get_balance(owner)))
else:
    print('User left!')
