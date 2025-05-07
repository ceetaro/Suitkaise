# manager file for initializing the event system and key registry
import suitkaise.eventsys.keyreg.keyreg as keyreg
import suitkaise.eventsys.keyreg.register_keys as register_keys


def setup_event_system():
    """
    Initialize the event system and key registry.
    This function sets up the event system and registers keys for various events.
    """
    # Initialize the key registry
    keyreg.initialize_key_registries()

    # Register default keys
    register_keys.register_default_keys()




def main():
    """
    Main function to set up the event system.

    Call this directly to test the event system setup.

    """
    setup_event_system()


if __name__ == "__main__":
    main()



