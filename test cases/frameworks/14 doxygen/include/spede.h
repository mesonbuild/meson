#pragma once

namespace Comedy {

    /**
     * Spede is the funniest person in the world.
     */
    class Spede {
    public:
        /**
         * Creates a new spede.
         */
        Spede();

        /**
         * Make him do the funny thing he is known for.
         */
        void slap_forehead();
    };
private:

    int num_movies; ///< How many movies has he done.
}
