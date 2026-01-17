
// Legacy "Bank System" Main Entry
#include <iostream>

// Global hack
int global_counter = 0;

void log_transaction();
void calculate_interest();
void update_balance();

void process_client() {
    log_transaction();
    calculate_interest();
    update_balance();
}

void main_loop() {
    process_client();
    // Infinite recursion potential? No, just loop.
    if (global_counter < 10) {
        global_counter++;
        main_loop(); 
    }
}

int main() {
    std::cout << "Starting Bank System..." << std::endl;
    main_loop();
    return 0;
}
