pragma circom 2.0.0;

template Quadratic() {
    signal input x;
    signal input a;
    signal input b;
    signal input c;
    signal output result;
    
    signal x_squared;
    signal ax_squared;
    signal bx;
    signal temp;
    
    // Each constraint can only have ONE multiplication
    x_squared <== x * x;           // Constraint 1: x^2
    ax_squared <== a * x_squared;  // Constraint 2: a * x^2
    bx <== b * x;                  // Constraint 3: b * x
    temp <== ax_squared + bx;      // Linear combination
    result <== temp + c;           // Linear combination
}

component main = Quadratic();