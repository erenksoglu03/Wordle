from random import choice
import yaml
from rich.console import Console
from collections import Counter

class Guesser:
    '''
        Wordle Solver:
        - The first guess is optimized using letter frequency analysis.
        - The second guess dynamically adapts based on feedback from the first guess.
        - Subsequent guesses prioritize narrowing down search space efficiently.
    '''
    def __init__(self, manual):
        self.word_list = yaml.load(open('wordlist.yaml'), Loader=yaml.FullLoader)
        self._manual = manual
        self.console = Console()
        
        self._tried = []
        self.first_guess = self.analysis(self.word_list, allow_duplicates=False)  # Run letter frequency analysis for the first guess

        self._invalid_letters = set()   # Letters confirmed as NOT in the word
        self._correct_positions = [''] * 5  # Correct letters in their positions
        self._misplaced_letters = {}  # Letters in the word but in the wrong position

        self.guess_count = 0
        self.first_guess_letters = set(self.first_guess)  # Track letters used in the first guess

    def restart_game(self):
        """Resets the solver for a new game."""
        self._tried = []
        self._invalid_letters = set()
        self._correct_positions = [''] * 5
        self._misplaced_letters = {}
        self.guess_count = 0
        self.first_guess_letters = set(self.first_guess)

    def analysis(self, word_list, allow_duplicates=False):
        """
        Optimized first-guess selection based on letter frequency.
        - Determines the most frequent letters and their best positions and avoids duplicate letters.
        """
        letter_frequency = [{} for _ in range(5)]
        overall_frequency = {}

        # Calculate letter frequency for each position
        for word in word_list:
            for i in range(5):
                letter = word[i]
                letter_frequency[i][letter] = letter_frequency[i].get(letter, 0) + 1
                overall_frequency[letter] = overall_frequency.get(letter, 0) + 1

        # Sort letters by frequency for each position
        sorted_letter_frequency = [
            sorted(freq.items(), key=lambda item: item[1], reverse=True)
            for freq in letter_frequency
        ]

        # Find the five most frequent letters overall (sorted in descending order)
        sorted_overall_letters = sorted(overall_frequency.keys(), key=lambda l: overall_frequency[l], reverse=True)
        top_five_letters = sorted_overall_letters[:5]  # Take only the top 5 most used letters

        # Assign the top 5 letters to their most common position in order of frequency
        chosen_word = [''] * 5  # Initialize empty word
        used_letters = set()

        for letter in top_five_letters:
            best_position = None
            highest_freq = -1  # Track highest frequency position

            # Find the most frequent available position for this letter
            for pos in range(5):
                if letter in dict(sorted_letter_frequency[pos]) and chosen_word[pos] == '':
                    letter_freq = dict(sorted_letter_frequency[pos])[letter]
                    if letter_freq > highest_freq:
                        best_position = pos
                        highest_freq = letter_freq  # Update the best position based on frequency

            # Assign letter to its most common available position
            if best_position is not None:
                chosen_word[best_position] = letter
                used_letters.add(letter)

        # Fill any remaining empty positions with the remaining top letters
        for i in range(5):
            if chosen_word[i] == '':
                for letter in top_five_letters:
                    if letter not in used_letters:
                        chosen_word[i] = letter
                        used_letters.add(letter)
                        break

        chosen_word_str = "".join(chosen_word)
        #self.console.print(f"Choosing word based on frequency: {chosen_word_str}")
        return chosen_word_str


    def get_guess(self, result):
        '''
        Determines the next guess:
        - First guess uses letter frequency analysis.
        - Second guess adapts based on information from the first.
        - Later guesses optimize search space reduction.
        '''
        if self._manual == 'manual':
            return self.console.input('Your guess:\n')

        if not self._tried:
            guess = self.first_guess  # Start with optimized first guess
            
        else:
            last_guess = self._tried[-1]
            #print(f"Last guess: {last_guess}")  # Debug statement

            if len(last_guess) != 5:
                raise ValueError("Last guess must be a 5-letter word")

            # Process feedback from Wordle and parse it.
            for i, char in enumerate(result):
                if char.isalpha():  
                    self._correct_positions[i] = last_guess[i]  
                    if last_guess[i] in self._invalid_letters:
                        self._invalid_letters.remove(last_guess[i])
                elif char == '-':  
                    if last_guess[i] not in self._misplaced_letters:
                        self._misplaced_letters[last_guess[i]] = set()
                    self._misplaced_letters[last_guess[i]].add(i)
                elif char == '+':  
                    if last_guess[i] not in self._misplaced_letters and last_guess[i] not in self._correct_positions:
                        self._invalid_letters.add(last_guess[i])

            # Filter the word list based on known information
            filtered_word_list = [
                word for word in self.word_list
                if not any(letter in word for letter in self._invalid_letters) and
                not any(self._correct_positions[i] and word[i] != self._correct_positions[i] for i in range(5)) and
                not any(letter in self._misplaced_letters and i in self._misplaced_letters[letter] for i, letter in enumerate(word)) and
                all(letter in word for letter in self._misplaced_letters)  
            ]                

            #print(f'Length of available words = {len(filtered_word_list)}')
            #print(f'Filtered word list: {filtered_word_list}')

            # Second Guess Optimization (Adaptive Strategy)
            if self.guess_count == 1:
                if len(self._misplaced_letters) > 2: # too many misplaced letters. better changing the places of the letters for the information gain
                    # Prioritize keeping misplaced letters in a new position
                    second_guess_list = [
                        word for word in filtered_word_list if all(letter in word for letter in self._misplaced_letters)
                    ]
                else:
                    # Choose high-entropy words that avoid first guess letters
                    letter_entropy = {letter: sum(1 for word in filtered_word_list if letter in word)
                                      for letter in set("".join(filtered_word_list))}
                    sorted_letters = sorted(letter_entropy, key=letter_entropy.get, reverse=True)

                    second_guess_list = [
                        word for word in filtered_word_list if not any(letter in self.first_guess_letters for letter in word)
                    ]

                # For too many misplaced letters situation, choose a word from the second_guess_list
                if second_guess_list:
                    guess = second_guess_list[0]

                else:
                    # Construct a second guess ensuring it reaches 5 letters
                    second_guess = []
                    used_letters = set()

                    for letter in sorted_letters:
                        if letter not in self.first_guess_letters and letter not in used_letters:
                            second_guess.append(letter)
                            used_letters.add(letter)
                        if len(second_guess) == 5:
                            break

                    # If still not 5 letters, fill remaining slots with highest entropy letters
                    if len(second_guess) < 5:
                        second_guess = choice(filtered_word_list)

                    guess = ''.join(second_guess)

                #print(f'Second guess based on entropy: {guess}')

            # Handling the edge case of a single missing letter
            elif self._correct_positions.count('') == 1 and len(filtered_word_list) > 3 and self.guess_count < 6:
                # Identify the position that is not yet correct
                missing_position = self._correct_positions.index('')

                # Find possible candidates for the missing letter
                possible_candidates = set(word[missing_position] for word in filtered_word_list)

                # Construct the guess using possible candidates
                guessie = list(possible_candidates)  # Convert set to list

                # If there are fewer than 5 letters, fill the rest with random letters
                while len(guessie) < 5:
                    guessie.append(choice('abcdefghijklmnopqrstuvwxyz'))  # Add random letters if needed

                # Convert list to string
                guess = ''.join(guessie[:5])  # Ensure it's exactly 5 characters long

                #print(f'Choosing based on possible candidates for position {missing_position}: {guess}')

            # Search-Space Splitting for Later Guesses
            elif filtered_word_list:
                word_scores = {
                    word: sum(1 for other_word in filtered_word_list if sum(a != b for a, b in zip(word, other_word)) == 1)
                    for word in filtered_word_list
                }
                guess = max(word_scores, key=word_scores.get)

            else:
                guess = choice(filtered_word_list)  

        # Ensure the solver does not make the same guess twice.
        while guess in self._tried:
            guess = choice(filtered_word_list)

        self._tried.append(guess)
        self.guess_count += 1  

       #self.console.print(f"Guessing: {guess}")
       #print(f'Self.tried = {self._tried}')
       #print(f'Self.correct_positions = {self._correct_positions}')
       #print(f'Self.misplaced_letters = {self._misplaced_letters}')
       #print(f'Self.invalid_letters = {self._invalid_letters}')
        return guess
