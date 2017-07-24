#include <vulkan/vulkan.h>
#include <stdio.h>

int main()
{
    VkInstanceCreateInfo instance_create_info = {
        	VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO,
        	NULL,
        	0,
        	NULL,
        	0,
        	NULL,
        	0,
        	NULL,
    };

    VkInstance instance;
    VkResult ret = vkCreateInstance(&instance_create_info, NULL, &instance);
    if(ret != VK_SUCCESS) {
        printf("Could not create vulkan instance: %d\n", ret);
      	return ret;
    }

    vkDestroyInstance(instance, NULL);
    return 0;    
}