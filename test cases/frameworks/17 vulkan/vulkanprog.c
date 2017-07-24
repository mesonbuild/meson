#include <vulkan/vulkan.h>
#include <stdio.h>

int main()
{
    VkApplicationInfo application_info = {
        VK_STRUCTURE_TYPE_APPLICATION_INFO,
        	NULL,
        	"sway",
        	VK_MAKE_VERSION(1,0,0),
        	"wlroots",
        	VK_MAKE_VERSION(1,0,0),
        	VK_MAKE_VERSION(1,0,0)
    };

    VkInstanceCreateInfo instance_create_info = {
        	VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO,
        	NULL,
        	0,
        	&application_info,
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

    return 0;    
}