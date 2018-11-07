memcpy(four, four_initial, sizeof(four_initial));
printf("Using %s.\n", type);
fptr(four);
for(i=0; i<4; i++) {
    if(four[i] != expected[i]) {
	printf("Increment function failed, got %f expected %f.\n", four[i], expected[i]);
	r=1;
    }
}
