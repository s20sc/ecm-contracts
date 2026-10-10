
#include "rclcpp/rclcpp.hpp"
#include <tf2_ros/buffer.h>
#include <tf2_ros/transform_listener.h>
#include <sensor_msgs/msg/image.hpp>
#include <functional>

class ListenerNode : public rclcpp::Node
{
public:
	explicit ListenerNode(const rclcpp::NodeOptions & options) :
		ListenerNode("listener", options)
	{}
	explicit ListenerNode(const std::string & name, const rclcpp::NodeOptions & options) :
		Node(name, options)
	{
		bool sub_topic = false;
		sub_topic = this->declare_parameter("sub_topic", sub_topic);

		tf_buffer_ = std::make_shared<tf2_ros::Buffer>(this->get_clock());
		tf_listener_ = std::make_shared<tf2_ros::TransformListener>(*tf_buffer_);

		if(sub_topic) {
			RCLCPP_INFO(get_logger(), "Subscribing to topic");
			sub_ = create_subscription<sensor_msgs::msg::Image>("/camera/image_raw", rclcpp::QoS(1), std::bind(&ListenerNode::callbackTopic, this, std::placeholders::_1));
		}
		else {
			RCLCPP_INFO(get_logger(), "Starting timer loop");
			lookup_timer_ = this->create_wall_timer(std::chrono::milliseconds(20), std::bind(&ListenerNode::callbackTimer, this));  
		}
	}

	void callbackTimer()
	{
		getTransform(now());
	}

	void callbackTopic(const sensor_msgs::msg::Image::ConstSharedPtr image)
	{
		getTransform(image->header.stamp);
	}

	void getTransform(const rclcpp::Time & stamp)
	{
		double start = now().seconds();
		try
		{
			geometry_msgs::msg::TransformStamped tmp;
			tmp = tf_buffer_->lookupTransform("odom", "base_link", stamp, rclcpp::Duration::from_seconds(0.5));
		}
		catch(tf2::TransformException & ex)
		{
			RCLCPP_ERROR(get_logger(), "%s (timeout=%.3fs)", ex.what(), 0.5);
		}
		double end = now().seconds();
		if(end - start > max_wait_time_) {
			max_wait_time_ = end - start;
		}

		++count_;
		double stamp_now = now().seconds();
		double interval = stamp_now - last_call_;
		if(interval > max_interval_)
		{
			max_interval_ = interval;
		}
		if(stamp_now - reference_stamp_ >= 1.0)
		{
			RCLCPP_WARN(get_logger(), "Callback called %d times in the past %0.3f sec (max interval=%0.3f, max wait=%0.03f)", 
				count_, stamp_now - reference_stamp_, max_interval_, max_wait_time_);
			count_ = 0;
			max_interval_ = 0;
			reference_stamp_ = stamp_now;
			max_wait_time_ = 0;
		}
		last_call_ = stamp_now;
	}

	virtual ~ListenerNode() {

	}

private:
	std::shared_ptr<tf2_ros::Buffer> tf_buffer_;
	std::shared_ptr<tf2_ros::TransformListener> tf_listener_;
	rclcpp::TimerBase::SharedPtr lookup_timer_;
	rclcpp::Subscription<sensor_msgs::msg::Image>::SharedPtr sub_;
	int count_;
	double reference_stamp_;
	double last_call_;
	double max_interval_;
	double max_wait_time_;
};

int main(int argc, char** argv)
{
	rclcpp::init(argc, argv);
	rclcpp::spin(std::make_shared<ListenerNode>(rclcpp::NodeOptions()));
	rclcpp::shutdown();
	return 0;
}
