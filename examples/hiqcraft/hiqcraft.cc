#include <iostream>

int main(void) {
#if (defined(__X86_64__) && !defined(Q_CPU_ONLY))
  std::cout << "Hi, x86 there (gpu as default)." << std::endl;
#elif (defined(Q_CPU_ONLY) && defined(__X86_64__))
  std::cout << "Hi, x86 cpu there." << std::endl;
#elif defined(__J5__)
  std::cout << "Hi, J5 there." << std::endl;
#elif defined(__X9HP__)
  std::cout << "Hi, X9HP there." << std::endl;
#elif defined(__DRIVE_ORIN__)
  std::cout << "Hi, Drive Orin there." << std::endl;
#elif defined(__JETSON_ORIN__)
  std::cout << "Hi, Jetson Orin there." << std::endl;
#else
  std::cout << "Hi! Test code, please input a macro compile optiton, like "
               "'--copt -D__DRIVE_ORIN__'."
            << std::endl;
#endif
  return 0;
}
